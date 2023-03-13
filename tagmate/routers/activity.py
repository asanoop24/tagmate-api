import time
import uuid
import datetime
from os import getenv as env
from os.path import join as joinpath
from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
import redis  # type: ignore

from fastapi import APIRouter, Depends, File, Form, UploadFile
from tortoise import exceptions as TortoiseExceptions

from tagmate.exceptions import activity as ActivityExceptions
from tagmate.exceptions import auth as AuthExceptions
from tagmate.models.db.activity import Activity as ActivityTable
from tagmate.models.db.activity import Document as DocumentTable
from tagmate.models.db.user import User as UserTable
from tagmate.models.py.activity import (
    Activity,
    ActivityCreate,
    ActivityId,
    ActivityStatus,
    Document,
)
from tagmate.models.enums import ActivityStatusEnum, ActivityTaskEnum
from tagmate.models.py.user import User
from tagmate.storage.minio import MinioObjectStore
from tagmate.utils.constants import UPLOADS_BUCKET, DATASET_INDEX_COLUMN_NAME, DATASET_TEXT_COLUMN_NAME
from tagmate.utils.auth import authenticate_with_token
from tagmate.utils.functions import bytes_to_df
from tagmate.utils.validations import validate_activity_exists, validate_user_exists



router = APIRouter(prefix="/activity", tags=["activity"])


@router.post("/create", response_model=ActivityStatus)
async def create_activity(
    name: str = Form(..., description="name of the activity"),
    task: str = Form(..., description="task of the activity"),
    data: UploadFile = File(..., description="data for the activity"),
    email: str = Depends(authenticate_with_token),
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)

    user_id = str(user.id)
    activity_id = str(uuid.uuid4())

    file_name = data.filename
    storage_path = joinpath(user_id, activity_id, file_name)

    try:
        client = MinioObjectStore()

        if not client.bucket_exists(UPLOADS_BUCKET):
            client.create_bucket(UPLOADS_BUCKET)

        bytes_data = await data.read()

        client.upload_object_from_bytes(
            bucket_name=UPLOADS_BUCKET,
            object_name=storage_path,
            data=bytes_data,
            length=len(bytes_data),
        )
    except Exception as exc:
        raise ActivityExceptions.FileUploadError(exception=exc)

    await ActivityTable.create(
        id=activity_id,
        name=name,
        task=task,
        user_id=user_id,
        file_name=file_name,
        storage_path=storage_path,
    )

    df = bytes_to_df(bytes_data)
    df = df.rename(columns={"review": DATASET_TEXT_COLUMN_NAME})

    documents = df[[DATASET_INDEX_COLUMN_NAME, DATASET_TEXT_COLUMN_NAME]].to_dict(
        orient="records"
    )

    await DocumentTable.bulk_create(
        [
            DocumentTable(
                index=doc[DATASET_INDEX_COLUMN_NAME],
                text=doc[DATASET_TEXT_COLUMN_NAME],
                activity_id=activity_id,
            )
            for doc in documents
        ]
    )

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.CREATED)


@router.get("/list", response_model=list[Activity])
async def fetch_all_activities(email: str = Depends(authenticate_with_token)):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)

    user_id = user.id

    try:
        activities = await ActivityTable.filter(user_id=user_id)
    except TortoiseExceptions.DoesNotExist:
        activities = []

    return activities


@router.get("/{activity_id}", response_model=Activity)
async def fetch_one_activity(
    activity_id: str, email: str = Depends(authenticate_with_token)
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    activity = await validate_activity_exists(user_id, activity_id)

    return Activity(**activity)


@router.get("/{activity_id}/data", response_model=list[Document])
async def fetch_activity_data(
    activity_id: str, email: str = Depends(authenticate_with_token)
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    activity = await validate_activity_exists(user_id, activity_id)

    storage_path = activity.storage_path

    try:
        client = MinioObjectStore()
        bytes_data = client.download_object_as_bytes(
            bucket_name=UPLOADS_BUCKET, object_name=storage_path
        )
    except Exception as exc:
        raise ActivityExceptions.FileDownloadError(exception=exc)

    df = bytes_to_df(bytes_data)
    df = df.rename(columns={"review": "text"})

    documents = df[["index", "text"]].to_dict(orient="records")

    return [Document(**doc) for doc in documents]


@router.get("/{activity_id}/load", response_model=list[Document])
async def fetch_activity_data(
    activity_id: str, email: str = Depends(authenticate_with_token)
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    await validate_activity_exists(user_id, activity_id)

    try:
        documents = await DocumentTable.filter(activity_id=activity_id)
    except TortoiseExceptions.DoesNotExist:
        documents = []

    return documents


@router.post("/{activity_id}/save", response_model=ActivityStatus)
async def fetch_activity_data(
    activity_id: str,
    documents: list[Document],
    email: str = Depends(authenticate_with_token),
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    await validate_activity_exists(user_id, activity_id)

    try:
        await DocumentTable.bulk_update(
            objects=[DocumentTable(id=doc.id, labels=doc.labels, updated_at=datetime.datetime.utcnow()) for doc in documents],
            fields=["labels", "updated_at"],
        )
    except Exception as exc:
        raise ActivityExceptions.ActivitySaveError(exception=exc)

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.SAVED)


@router.post("/{activity_id}/train", response_model=ActivityStatus)
async def train_activity_model(
    activity_id: str,
    email: str = Depends(authenticate_with_token),
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    await validate_activity_exists(user_id, activity_id)

    try:
        arq_redis = await create_pool(
            RedisSettings(host=env("REDIS_HOST", "redis"), port=env("REDIS_PORT", 6379))
        )
    except redis.exceptions.ConnectionError as e:
        raise ActivityExceptions.RedisConnectionError

    job = await arq_redis.enqueue_job(
        "train_multilabel_classifier",
        activity_id,
    )

    print(job)

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.TRAINING)

