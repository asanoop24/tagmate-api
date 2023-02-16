from os import getenv as env
from typing import Any
from io import BytesIO

from minio import Minio
from minio.datatypes import Bucket, Object

from tagmate.storage.base import BaseObjectStore


MINIO_HOST = env("MINIO_HOST", "minio")
MINIO_PORT = env("MINIO_PORT", 9000)
MINIO_ROOT_USER = env("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = env("MINIO_ROOT_PASSWORD", "minioadmin")


class MinioObjectStore(BaseObjectStore):
    def __init__(
        self,
        host: str = MINIO_HOST,
        port: int | str = MINIO_PORT,
        username: str = MINIO_ROOT_USER,
        password: str = MINIO_ROOT_PASSWORD,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.secure = False
        self.endpoint = f"{self.host}:{self.port}"

        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.username,
            secret_key=self.password,
            secure=self.secure,
        )

    def create_bucket(self, bucket_name: str) -> None:
        return self.client.make_bucket(bucket_name=bucket_name)

    def list_buckets(self) -> list[Bucket]:
        return list(self.client.list_buckets())

    def bucket_exists(self, bucket_name: str) -> bool:
        return self.client.bucket_exists(bucket_name=bucket_name)

    def list_objects(self, bucket_name: str) -> list[Object]:
        return self.client.list_objects(bucket_name=bucket_name)

    def upload_object_from_file(
        self, bucket_name: str, object_name: str, file_path: str
    ) -> None:
        self.client.fput_object(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=file_path,
            content_type="application/octet-stream",
        )

    def upload_object_from_bytes(
        self, bucket_name: str, object_name: str, data: bytes, length: int
    ) -> None:

        self.client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=BytesIO(data),
            length=length,
            content_type="application/octet-stream",
        )

    def download_object_as_bytes(self, bucket_name: str, object_name: str) -> bytes:
        response = self.client.get_object(
            bucket_name=bucket_name, object_name=object_name
        )
        return response.data

    def download_object_as_file(
        self, bucket_name: str, object_name: str, file_path: str
    ) -> None:
        self.client.fget_object(
            bucket_name=bucket_name, object_name=object_name, file_path=file_path
        )
