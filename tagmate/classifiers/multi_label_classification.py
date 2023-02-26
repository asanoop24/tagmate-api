import random
from os import listdir
from os.path import join as joinpath

from datasets import Dataset
from sentence_transformers.losses import CosineSimilarityLoss
from setfit import SetFitModel, SetFitTrainer
import pandas as pd

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
    def __init__(self, activity_id: str, job_logger: JobLogger):
        self.activity_id = activity_id
        self.logger = job_logger

    async def fetch_activity_from_db(self, activity_id: str):
        activity = await ActivityTable.get(id=activity_id)
        return activity

    async def fetch_activity_documents(self, activity_id: str):
        documents = await DocumentTable.filter(activity_id=activity_id)
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
        self.trainer.train()

    # def evaluate(self):
    #     metrics = self.trainer.evaluate()
    #     return metrics

    # def predict(self, data: str | list[str]):
    #     preds = self.model(data)
    #     return preds

    # def predict_proba(self, data: str | list[str]):
    #     probs = self.model.predict_proba(data)
    #     return probs

    def convert_documents_to_df(self, documents: list[DocumentTable]) -> pd.DataFrame:
        documents_list = [[doc.text, doc.labels] for doc in documents]
        documents_df = pd.DataFrame(data=documents_list, columns=["text", "label"])
        self.logger.info(f"df length: {documents_df.shape}")

        ### TODO: Remove after testing
        def get_random_label(x):
            return random.choice(["parking", "neighborhood", "maintenance", "pets"])

        documents_df["label"] = documents_df["label"].apply(get_random_label)
        self.logger.info(f"df length: {documents_df.shape}")
        return documents_df

    def convert_df_to_dataset(self, documents_df: pd.DataFrame) -> Dataset:
        documents_ds = Dataset.from_pandas(documents_df)
        return documents_ds

    async def save_model(self):
        activity = await ActivityTable.get(id=self.activity_id)
        user_id = str(activity.user_id)
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

    async def load_model(self):
        activity = await ActivityTable.get(id=self.activity_id)
        user_id = str(activity.user_id)
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

    async def train_classifier(self):
        await db_init()
        documents = await self.fetch_activity_documents(self.activity_id)
        documents_df = self.convert_documents_to_df(documents)
        documents_ds = self.convert_df_to_dataset(documents_df)
        await self.load_model()
        self.train(documents_ds)
        await self.save_model()
