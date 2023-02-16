from os import getenv as env
from os.path import join
from fastapi import Depends, APIRouter, Form, UploadFile, File
from tortoise import exceptions as TortoiseExceptions
import uuid
import time
import pandas as pd

from tagmate.models.py.user import User
from tagmate.models.py.activity import Activity, ActivityId, ActivityCreate, Document
from tagmate.models.db.user import User as UserTable
from tagmate.models.db.activity import Activity as ActivityTable
from tagmate.exceptions import auth as AuthExceptions, activity as ActivityExceptions
from tagmate.utils.auth import authenticate_with_token
from tagmate.storage.minio import MinioObjectStore


MINIO_BUCKET = env("MINIO_BUCKET", "tagmate")


router = APIRouter(prefix="/activity", tags=["activity"])


@router.post("/create", response_model=ActivityId)
async def create_activity(
    name: str = Form(..., description="name of the activity"),
    task: str = Form(..., description="task of the activity"),
    data: UploadFile = File(..., description="data for the activity"),
    email: str = Depends(authenticate_with_token),
):
    if not email:
        raise AuthExceptions.InvalidToken()

    try:
        user = await UserTable.get(email=email).values()
    except TortoiseExceptions.DoesNotExist:
        raise AuthExceptions.InvalidUsername()

    user_id = user.get("id")
    print(f"user_id: {user_id}")

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

    return ActivityId(id=_id)


@router.get("/list", response_model=list[Activity])
async def fetch_all_activities(email: str = Depends(authenticate_with_token)):
    if not email:
        raise AuthExceptions.InvalidToken()

    try:
        user = await UserTable.get(email=email)
    except TortoiseExceptions.DoesNotExist:
        raise AuthExceptions.InvalidUsername()

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

    try:
        user = await UserTable.get(email=email).values()
    except TortoiseExceptions.DoesNotExist:
        raise AuthExceptions.InvalidUsername()

    user_id = user.get("id")
    print(f"user_id: {user_id}")

    print(activity_id)
    try:
        activity = await ActivityTable.get(user_id=user_id, id=activity_id).values()
    except TortoiseExceptions.DoesNotExist:
        activity = []

    return Activity(**activity)


@router.get("/{activity_id}/data", response_model=list[Document])
async def fetch_activity_data(
    activity_id: str, email: str = Depends(authenticate_with_token)
):
    if not email:
        raise AuthExceptions.InvalidToken()

    try:
        user = await UserTable.get(email=email)
    except TortoiseExceptions.DoesNotExist:
        raise AuthExceptions.InvalidUsername()

    user_id = user.id
    print(f"user_id: {user_id}")

    print(activity_id)
    try:
        activity = await ActivityTable.get(user_id=user_id, id=activity_id)
    except TortoiseExceptions.DoesNotExist:
        activity = []

    storage_path = activity.storage_path
    from io import StringIO


    try:
        client = MinioObjectStore()
        bytes_data = client.download_object_as_bytes(
            bucket_name=MINIO_BUCKET, object_name=storage_path
        )
        print(type(bytes_data))
    except Exception as err:
        raise ActivityExceptions.FileDownloadError(detail=f"{type(err)}: {err}")
    
    s = str(bytes_data, "utf-8")
    data = StringIO(s)
    df = pd.read_csv(data).reset_index().rename(columns={"review": "text"})
    documents = df[["index", "text"]].to_dict(orient="records")

    return [Document(**doc) for doc in documents]
