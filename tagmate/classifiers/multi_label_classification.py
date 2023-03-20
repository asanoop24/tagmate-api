import random
from os import listdir
from os.path import join as joinpath

from datasets import Dataset
from sentence_transformers.losses import CosineSimilarityLoss
from setfit import SetFitModel, SetFitTrainer
import pandas as pd
import numpy as np
import torch

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
        self.is_multilabel = True

    async def fetch_activity_from_db(self):
        self.activity = await ActivityTable.get(id=self.activity_id)

    async def get_activity_documents(self):
        self.documents = await DocumentTable.filter(activity_id=self.activity_id)

    @staticmethod
    def get_object_store():
        return MinioObjectStore()

    def train(self):
        self.trainer = SetFitTrainer(
            model=self.model,
            train_dataset=self.tagged_documents_ds,
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

    async def get_activity_tags(self):
        self.tags = sorted(self.activity.tags)
        # self.tags = sorted(["maintenance", "neighborhood", "parking", "pets"])
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

    def convert_documents_to_df(self) -> None:
        documents_list = [[doc.id, doc.text, doc.labels] for doc in self.documents]
        documents_df = pd.DataFrame(
            data=documents_list, columns=["id", "text", "label"]
        )
        self.tagged_documents_df = documents_df[
            documents_df["label"].apply(lambda x: len(x)) > 0
        ].reset_index(drop=True)[["text", "label"]]
        self.untagged_documents_df = documents_df[
            documents_df["label"].apply(lambda x: len(x)) == 0
        ].reset_index(drop=True)
        self.tagged_documents_df["label"] = self.tagged_documents_df["label"].apply(
            self.encode_labels
        )
        self.logger.info(f"tagged df length: {self.tagged_documents_df[:10]}")
        self.logger.info(f"untagged df length: {self.untagged_documents_df[:3]}")

    def convert_df_to_dataset(self) -> None:
        self.tagged_documents_ds = Dataset.from_pandas(self.tagged_documents_df)

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
                self.model = SetFitModel.from_pretrained(
                    MODEL_ID, multi_target_strategy="one-vs-rest"
                )
            else:
                self.logger.info(f"Found an earlier model version with id: {MODEL_ID}")
                self.model = SetFitModel.from_pretrained(tmpdir)
        # TODO: Remove this and fix in the original line
        self.model = SetFitModel.from_pretrained(
            MODEL_ID, multi_target_strategy="one-vs-rest"
        )

    def generate_predictions(self):
        # self.load_model()
        texts = self.untagged_documents_df["text"].tolist()
        preds = self.model(texts)
        self.logger.info(preds)
        self.preds = [
            [self.label_decoder[idx.item()] for idx in torch.argwhere(pred == 1)]
            for pred in preds
        ]

    async def save_predictions(self):
        documents_to_save = [
            DocumentTable(id=row["id"], labels=self.preds[idx], is_auto_generated=True)
            for idx, row in self.untagged_documents_df.iterrows()
        ]
        await DocumentTable.bulk_update(
            objects=documents_to_save, fields=["labels", "is_auto_generated"]
        )

    async def train_classifier(self):
        await db_init()
        await self.fetch_activity_from_db()
        await self.get_activity_tags()

        await self.get_activity_documents()
        self.convert_documents_to_df()
        self.convert_df_to_dataset()

        self.load_model()
        self.train()
        self.save_model()
        self.generate_predictions()
        await self.save_predictions()
        # self.logger.info(
        #     f"model generated prediction: {self.predict(['Items are highly priced compared to local market!'])}"
        # )
