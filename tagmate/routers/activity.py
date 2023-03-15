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
from tagmate.models.db.activity import (
    Activity as ActivityTable,
    ActivityUserMap as ActivityUserTable,
)
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
from tagmate.utils.constants import (
    UPLOADS_BUCKET,
    DATASET_INDEX_COLUMN_NAME,
    DATASET_TEXT_COLUMN_NAME,
)
from tagmate.utils.auth import authenticate_with_token
from tagmate.utils.functions import bytes_to_df
from tagmate.utils.validations import validate_activity_exists, validate_user_exists
from tagmate.logging.app import logger


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

    await ActivityUserTable.create(
        activity_id=activity_id,
        user_id=user_id,
        is_owner=True,
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
        my_activities = await ActivityTable.filter(user_id=user_id)

        shared_activity_ids = await ActivityUserTable.filter(
            user_id=user_id, is_owner=False
        ).values("activity_id")
        shared_activity_ids = [a.get("activity_id") for a in shared_activity_ids]
        shared_activities = await ActivityTable.filter(id__in=shared_activity_ids)

        activities = my_activities + shared_activities
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

    await validate_activity_exists(user_id, activity_id)
    try:
        activity = await ActivityTable.get(id=activity_id)
        logger.info(activity)
    except TortoiseExceptions.DoesNotExist:
        activity = []

    return activity


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


@router.get("/{activity_id}/users", response_model=list[User])
async def fetch_activity_users(
    activity_id: str, email: str = Depends(authenticate_with_token)
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    await validate_activity_exists(user_id, activity_id)

    try:
        user_ids = await ActivityUserTable.filter(activity_id=activity_id).values(
            "user_id"
        )
        user_ids = [u.get("user_id") for u in user_ids]
        users = await UserTable.filter(id__in=user_ids)
    except TortoiseExceptions.DoesNotExist:
        users = []

    # TODO: Remove password hash from the response
    return users


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
            objects=[
                DocumentTable(
                    id=doc.id, labels=doc.labels, updated_at=datetime.datetime.utcnow()
                )
                for doc in documents
            ],
            fields=["labels", "updated_at"],
        )
    except Exception as exc:
        raise ActivityExceptions.ActivitySaveError(exception=exc)

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.SAVED)


@router.post("/{activity_id}/share", response_model=ActivityStatus)
async def fetch_activity_data(
    activity_id: str,
    share_email: str,
    email: str = Depends(authenticate_with_token),
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    await validate_activity_exists(user_id, activity_id)

    share_user = await validate_user_exists(share_email)
    share_user_id = share_user.id

    try:
        assert user_id != share_user_id
    except AssertionError as exc:
        raise AuthExceptions.InvalidUsername()

    try:
        await ActivityUserTable.create(
            activity_id=activity_id,
            user_id=share_user_id,
            is_owner=False,
        )
    except Exception as exc:
        raise ActivityExceptions.ActivitySaveError(exception=exc)

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.SHARED)


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


@router.delete("/{activity_id}", response_model=ActivityStatus)
async def fetch_activity_data(
    activity_id: str,
    email: str = Depends(authenticate_with_token),
):
    if not email:
        raise AuthExceptions.InvalidToken()

    user = await validate_user_exists(email)
    user_id = user.id

    activity = await validate_activity_exists(user_id, activity_id)

    try:
        await ActivityTable.delete(activity)
    except Exception as exc:
        raise ActivityExceptions.ActivityDeleteError(exception=exc)

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.DELETED)
