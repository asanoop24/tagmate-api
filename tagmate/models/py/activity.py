import uuid
from enum import Enum

from fastapi import UploadFile
from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator

from tagmate.models.db import activity

Activity = pydantic_model_creator(activity.Activity)
Document = pydantic_model_creator(
    activity.Document, optional=("created_at", "index", "text")
)


class ActivityCreate(BaseModel):
    name: str
    task: str
    dataset: UploadFile


class ActivityId(BaseModel):
    id: uuid.UUID


class ActivityTaskEnum(str, Enum):
    EntityClassification = "entity_classification"
    MultiLabelClassification = "multi_label_classification"


class ActivityStatusEnum(str, Enum):
    created = "created"
    in_progress = "in_progress"
    incomplete = "incomplete"
    completed = "completed"
    saved = "saved"
    shared = "shared"
    deleted = "deleted"


class ActivityStatus(BaseModel):
    id: uuid.UUID
    status: ActivityStatusEnum
