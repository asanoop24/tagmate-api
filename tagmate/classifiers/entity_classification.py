from tagmate.classifiers.base import Classifier
from datasets import Dataset
from sentence_transformers.losses import CosineSimilarityLoss

from setfit import SetFitModel, SetFitTrainer


FEW_SHOT_MODEL_NAME = "sentence-transformers/paraphrase-mpnet-base-v2"
BATCH_SIZE = 4
NUM_ITERATIONS = 20


class EntityClassifier(Classifier):
    def __init__(self, model_name: str | None = FEW_SHOT_MODEL_NAME, model_path: str | None = None):
        self.model = SetFitModel.from_pretrained(model_name)

    def train(self, train_ds: Dataset, eval_ds: Dataset | None = None):
        self.trainer = SetFitTrainer(
            model=self.model,
            train_dataset=train_ds,
            eval_dataset=eval_ds,
            loss_class=CosineSimilarityLoss,
            metric="accuracy",
            batch_size=BATCH_SIZE,
            num_iterations=NUM_ITERATIONS,  # The number of text pairs to generate for contrastive learning
            num_epochs=1,  # The number of epochs to use for contrastive learning
            column_mapping={
                "sentence": "text",
                "label": "label",
            },  # Map dataset columns to text/label expected by trainer
        )
        self.trainer.train()

    def evaluate(self):
        metrics = self.trainer.evaluate()
        return metrics

    def predict(data: str | list[str]):
        pass

    def save(self):
        pass