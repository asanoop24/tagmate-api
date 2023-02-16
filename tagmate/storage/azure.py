# from os import getenv as env
# from typing import Any

# from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
# from azure.storage.blob._models import BlobType

# from slabs.storage.base import BaseObjectStore


# AZURE_STORAGE_URI = env("AZURE_STORAGE_URI", None)


# class AzureObjectStore(BaseObjectStore):
#     def __init__(self, connection_string: str | None = AZURE_STORAGE_URI):
#         self.connection_string = connection_string
#         self.client = BlobServiceClient.from_connection_string(AZURE_STORAGE_URI)

#     def create_bucket(self, bucket_name: str) -> ContainerClient:
#         return self.client.create_container(bucket_name)

#     def list_buckets(self) -> list[ContainerClient]:
#         return list(self.client.list_containers())

#     def bucket_exists(self, bucket_name: str) -> bool:
#         return self.client.get_container_client(container=bucket_name).exists()

#     def list_objects(self, bucket_name: str) -> list[BlobClient]:
#         return self.client.get_container_client(container=bucket_name).list_blobs()

#     def upload_object_from_file(self, bucket_name: str, object_name: str, file_path: str) -> BlobClient:
#         with open(file_path, "rb") as f:
#             data = f.read()
#             self.client.get_container_client(container=bucket_name).upload_blob(
#                 name=object_name, data=data, length=len(data), blob_type=BlobType.BLOCKBLOB
#             )

#     def upload_object_from_bytes(self, bucket_name: str, object_name: str, data: Any) -> BlobClient:
#         self.client.get_container_client(container=bucket_name).upload_blob(
#             name=object_name, data=data, length=len(data), blob_type=BlobType.BLOCKBLOB
#         )

#     def download_object_as_bytes(self, bucket_name: str, object_name: str) -> bytes:
#         response = self.client.get_container_client(container=bucket_name).download_blob(blob=object_name)
#         return response.readall()

#     def download_object_as_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
#         response = self.client.get_container_client(container=bucket_name).download_blob(blob=object_name)
#         with open(file_path, "wb") as f:
#             response.readinto(f)
