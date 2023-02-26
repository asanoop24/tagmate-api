from abc import ABC, abstractmethod
from typing import Any


class BaseObjectStore(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def create_bucket(self, bucket_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_buckets(self) -> list:
        raise NotImplementedError

    @abstractmethod
    def upload_object_from_file(self, bucket_name: str, object_name: str, file_path: str):
        raise NotImplementedError

    @abstractmethod
    def upload_objects_from_folder(self, bucket_name: str, object_name: str, file_path: str):
        raise NotImplementedError

    @abstractmethod
    def upload_object_from_bytes(self, bucket_name: str, object_name: str, data: Any):
        raise NotImplementedError

    @abstractmethod
    def download_object_as_file(self, bucket_name: str, object_name: str, file_path: str):
        raise NotImplementedError

    @abstractmethod
    def download_object_as_bytes(self, bucket_name: str, object_name: str):
        raise NotImplementedError
