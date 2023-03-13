import random
from os import listdir
from os.path import join as joinpath

from datasets import Dataset
from sentence_transformers.losses import CosineSimilarityLoss
from setfit import SetFitModel, SetFitTrainer
import pandas as pd
import numpy as np

from tagmate.classifiers.base import Classifier
from tagmate.models.db.activity import (
    Activity as ActivityTable,
    Document as DocumentTable,
)
from tagmate.logging.worker import JobLogger
from tagmate.storage.minio import MinioObjectStore
from tagmate.utils.constants import MODELS_BUCKET
from tagmate.utils.database import db_init
from tagmate.utils.functions import SoftTemporaryDirectory


MODEL_ID = "sentence-transformers/paraphrase-mpnet-base-v2"
BATCH_SIZE = 4
NUM_ITERATIONS = 2
METRIC = "accuracy"


class MultiLabelClassifier(Classifier):
    def __init__(self, activity_id: str, logger: JobLogger | None = None):
        self.activity_id = activity_id
        self.logger = logger
        self.is_multilabel = False

    async def fetch_activity_from_db(self):
        self.activity = await ActivityTable.get(id=self.activity_id)

    async def get_activity_documents(self):
        documents = await DocumentTable.filter(activity_id=self.activity_id)
        return documents

    @staticmethod
    def get_object_store():
        return MinioObjectStore()

    def train(self, train_ds: Dataset, eval_ds: Dataset | None = None):
        self.trainer = SetFitTrainer(
            model=self.model,
            train_dataset=train_ds,
            eval_dataset=eval_ds,
            loss_class=CosineSimilarityLoss,
            metric=METRIC,
            batch_size=BATCH_SIZE,
            num_iterations=NUM_ITERATIONS,
            num_epochs=1,
        )
        # self.trainer.train()

    # def evaluate(self):
    #     metrics = self.trainer.evaluate()
    #     return metrics

    # def predict(self, data: str | list[str]):
    #     preds = self.model(data)
    #     return preds

    # def predict_proba(self, data: str | list[str]):
    #     probs = self.model.predict_proba(data)
    #     return probs

    async def get_activity_tags(self):
        # self.tags = self.activity.tags.sort()
        self.tags = sorted(["maintenance", "neighborhood", "parking", "pets"])
        self.label_encoder = {tag: idx for idx, tag in enumerate(self.tags)}
        self.label_decoder = {idx: tag for idx, tag in enumerate(self.tags)}

    def encode_labels(self, label: list[str] | str):
        if self.is_multilabel:
            encoded = np.zeros(len(self.tags), dtype=int)
            for lbl in label:
                encoded[self.label_encoder[lbl]] = 1
        else:
            encoded = self.label_encoder[label]
        return encoded

    def convert_documents_to_df(self, documents: list[DocumentTable]) -> pd.DataFrame:
        documents_list = [[doc.text, doc.labels] for doc in documents]
        documents_df = pd.DataFrame(data=documents_list, columns=["text", "label"])
        self.logger.info(f"df length: {documents_df.shape}")

        ### TODO: Remove after testing
        def get_random_label(x):
            if self.is_multilabel:
                return [
                    random.choice(["parking", "neighborhood", "maintenance", "pets"])
                ]
            else:
                return random.choice(["parking", "neighborhood", "maintenance", "pets"])

        documents_df["label"] = (
            documents_df["label"].apply(get_random_label).apply(self.encode_labels)
        )
        self.logger.info(f"df length: {documents_df[:3]}")
        return documents_df

    def convert_df_to_dataset(self, documents_df: pd.DataFrame) -> Dataset:
        documents_ds = Dataset.from_pandas(documents_df)
        return documents_ds

    def save_model(self):
        user_id = str(self.activity.user_id)
        storage_path = joinpath(user_id, self.activity_id)

        with SoftTemporaryDirectory() as tmpdir:
            local_storage_path = joinpath(tmpdir, self.activity_id)
            self.trainer.model.save_pretrained(save_directory=local_storage_path)
            client = self.get_object_store()
            client.upload_objects_from_folder(
                bucket_name=MODELS_BUCKET,
                objects_path=storage_path,
                folder_path=local_storage_path,
            )

    def load_model(self):
        user_id = str(self.activity.user_id)
        storage_path = joinpath(user_id, self.activity_id)
        client = self.get_object_store()

        with SoftTemporaryDirectory() as tmpdir:
            client.download_objects_as_folder(
                bucket_name=MODELS_BUCKET,
                objects_path=storage_path,
                folder_path=tmpdir,
            )
            if len(listdir(tmpdir)) == 0:
                self.logger.info(
                    f"Could not find an earlier model version, loading pretrained model from hub with id: {MODEL_ID}"
                )
                self.model = SetFitModel.from_pretrained(MODEL_ID)
            else:
                self.logger.info(f"Found an earlier model version with id: {MODEL_ID}")
                self.model = SetFitModel.from_pretrained(tmpdir)

    def predict(self, texts: list[str]):
        self.load_model()
        return [self.label_decoder[pred.item()] for pred in self.model(texts)]

    async def train_classifier(self):
        await db_init()
        await self.get_activity_tags()
        await self.fetch_activity_from_db()

        documents = await self.get_activity_documents()
        documents_df = self.convert_documents_to_df(documents)
        documents_ds = self.convert_df_to_dataset(documents_df)

        self.load_model()
        self.train(documents_ds)
        self.save_model()
        self.logger.info(
            f"model generated prediction: {self.predict(['Items are highly priced compared to local market!'])}"
        )
