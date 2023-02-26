import uuid

from fastapi import UploadFile
from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator

from tagmate.models.db import activity
from tagmate.models.enums import ActivityStatusEnum


Activity = pydantic_model_creator(activity.Activity)
Document = pydantic_model_creator(
    activity.Document, optional=("created_at", "updated_at", "index", "text")
)


class ActivityCreate(BaseModel):
    name: str
    task: str
    dataset: UploadFile


class ActivityId(BaseModel):
    id: uuid.UUID


class ActivityStatus(ActivityId):
    status: ActivityStatusEnum
