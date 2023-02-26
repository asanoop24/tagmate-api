from abc import ABC, abstractmethod


class Classifier(ABC):
    @abstractmethod
    def train(self, train_ds):
        pass

    # @abstractmethod
    # def evaluate(eval_ds):
    #     pass

    # def predict(data: str | list[str]):
    #     pass
