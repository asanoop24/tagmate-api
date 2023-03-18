import uuid
from tortoise import Tortoise

from fastapi import UploadFile
from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator

from tagmate.models.db.activity import Activity as ActivityTable, Document as DocumentTable
from tagmate.models.enums import ActivityStatusEnum

# Tortoise.init_models(["tagmate.models.db.user", "tagmate.models.db.activity"], "models")

Activity = pydantic_model_creator(ActivityTable)
Document = pydantic_model_creator(
    DocumentTable, optional=("created_at", "updated_at", "index", "text")
)


class ActivityCreate(BaseModel):
    name: str
    task: str
    dataset: UploadFile


class ActivityId(BaseModel):
    id: uuid.UUID


class ActivityStatus(ActivityId):
    status: ActivityStatusEnum
