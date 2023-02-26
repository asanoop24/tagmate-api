from os import getenv as env, listdir
from os.path import isdir, isfile, join as joinpath
from typing import Any
from io import BytesIO
import logging

logger = logging.getLogger("arq.worker")

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

    def upload_objects_from_folder(
        self, bucket_name: str, objects_path: str, folder_path: str
    ):
        for f in listdir(folder_path):
            f_path = joinpath(folder_path, f)
            object_name = joinpath(objects_path, f)
            if isdir(f_path):
                self.upload_objects_from_folder(
                    bucket_name=bucket_name,
                    objects_path=object_name,
                    folder_path=f_path,
                )
            elif isfile(f_path):
                self.upload_object_from_file(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=f_path,
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

    def download_objects_as_folder(
        self, bucket_name: str, objects_path: str, folder_path: str
    ):
        for obj in self.client.list_objects(
            bucket_name=bucket_name, prefix=objects_path, recursive=False
        ):
            if obj.is_dir:
                sub_folder_path = joinpath(
                    folder_path, obj.object_name.removeprefix(objects_path).strip("/")
                )
                self.download_objects_as_folder(
                    bucket_name=bucket_name,
                    objects_path=obj.object_name,
                    folder_path=sub_folder_path,
                )
            else:
                file_path = joinpath(
                    folder_path, obj.object_name.removeprefix(objects_path)
                )
                self.download_object_as_file(
                    bucket_name=bucket_name,
                    object_name=obj.object_name,
                    file_path=file_path,
                )
