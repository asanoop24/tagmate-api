import time
import uuid
from os import getenv as env
from os.path import join

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
    ActivityStatusEnum,
    ActivityTaskEnum,
    Document,
)
from tagmate.models.py.user import User
from tagmate.storage.minio import MinioObjectStore
from tagmate.utils import constants as C
from tagmate.utils.auth import authenticate_with_token
from tagmate.utils.functions import bytes_to_df
from tagmate.utils.validations import validate_activity_exists, validate_user_exists

MINIO_BUCKET = env("MINIO_BUCKET", "tagmate")


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

    user_id = user.id

    # activities = await ActivityTable.get(user_id=user_id).values()
    # activity_exists = any([activity.name == act.name for act in activities])
    # if activity_exists:
    #     raise ActivityExceptions.ActivityAlreadyExists

    file_name = data.filename
    storage_path = join(str(user_id), f"{time.time_ns()}__{file_name}")

    try:
        client = MinioObjectStore()

        if not client.bucket_exists(MINIO_BUCKET):
            client.create_bucket(MINIO_BUCKET)

        bytes_data = await data.read()

        client.upload_object_from_bytes(
            bucket_name=MINIO_BUCKET,
            object_name=storage_path,
            data=bytes_data,
            length=len(bytes_data),
        )
    except Exception as err:
        raise ActivityExceptions.FileUploadError(detail=f"{type(err)}: {err}")

    _id = uuid.uuid4()
    await ActivityTable.create(
        id=_id,
        name=name,
        task=task,
        user_id=user_id,
        file_name=file_name,
        storage_path=storage_path,
    )

    df = bytes_to_df(bytes_data)
    df = df.rename(columns={"review": C.DATASET_TEXT_COLUMN_NAME})

    documents = df[[C.DATASET_INDEX_COLUMN_NAME, C.DATASET_TEXT_COLUMN_NAME]].to_dict(
        orient="records"
    )

    await DocumentTable.bulk_create(
        [
            DocumentTable(
                index=doc[C.DATASET_INDEX_COLUMN_NAME],
                text=doc[C.DATASET_TEXT_COLUMN_NAME],
                activity_id=_id,
            )
            for doc in documents
        ]
    )

    return ActivityStatus(id=_id, status=ActivityStatusEnum.created)


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
            bucket_name=MINIO_BUCKET, object_name=storage_path
        )
    except Exception as err:
        raise ActivityExceptions.FileDownloadError(detail=f"{type(err)}: {err}")

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
            objects=[DocumentTable(id=doc.id, labels=doc.labels) for doc in documents],
            fields=["labels"],
        )
    except Exception as err:
        raise ActivityExceptions.ActivitySaveError()

    return ActivityStatus(id=activity_id, status=ActivityStatusEnum.saved)
