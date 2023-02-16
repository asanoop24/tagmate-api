import uuid
from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator
from fastapi import UploadFile

from tagmate.models.db import activity


Activity = pydantic_model_creator(activity.Activity)


class ActivityCreate(BaseModel):
    name: str
    task: str
    dataset: UploadFile


class ActivityId(BaseModel):
    id: uuid.UUID


class Document(BaseModel):
    index: int
    text: str

# class Activity(BaseModel):
#     id: uuid.UUID
#     name: str
#     task: str
#     user_id: uuid.UUID
#     dataset_path: str
