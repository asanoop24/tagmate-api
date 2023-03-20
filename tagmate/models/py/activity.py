import uuid
from tortoise import Tortoise
from enum import Enum


from fastapi import UploadFile
from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator

from tagmate.models.db.activity import Activity as ActivityTable, Document as DocumentTable
from tagmate.models.enums import ActivityStatusEnum, JobStatusEnum

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


# class JobStatusEnum(str, Enum):
#     deferred = "deferred"
#     queued = "queued"
#     in_progress = "in_progress"
#     complete = "complete"
#     not_found = "not_found"
#     aborted = "aborted"
#     not_aborted = "not_aborted"
#     aborting = "aborting"

class JobStatus(BaseModel):
    id: uuid.UUID
    status: JobStatusEnum