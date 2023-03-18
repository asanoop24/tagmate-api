from tortoise import Tortoise, fields, run_async
from tortoise.models import Model

from tagmate.utils.database import DB_URI
from tagmate.models.enums import ActivityStatusEnum


class Activity(Model):  # type: ignore
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100)
    task = fields.CharField(max_length=100)
    file_name = fields.CharField(max_length=1000)
    tags = fields.JSONField(null=True)
    user = fields.ForeignKeyField(model_name="models.User", to_field="id")
    storage_path = fields.CharField(max_length=1000)
    status = fields.CharEnumField(enum_type=ActivityStatusEnum, default=ActivityStatusEnum.INPROGRESS)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class ActivityUserMap(Model):
    activity = fields.ForeignKeyField(model_name="models.Activity", to_field="id")
    user = fields.ForeignKeyField(model_name="models.User", to_field="id")
    is_owner = fields.BooleanField()
    created_at = fields.DatetimeField(auto_now_add=True)


class Document(Model):
    id = fields.UUIDField(pk=True)
    index = fields.IntField(null=True)
    text = fields.TextField(null=False)
    activity = fields.ForeignKeyField(model_name="models.Activity", to_field="id")
    labels = fields.JSONField(default=[], null=True)
    clusters = fields.JSONField(default=[], null=True)
    # user = fields.ForeignKeyField(model_name="models.User", to_field="id")
    # is_auto_generated = fields.BooleanField(default=False, description="True if the labels for the document are suggested by the Few Shot Classifier")
    # is_user_validated = fields.BooleanField(default=True, description="True if the suggested labels have been validated by the user")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Cluster(Model):
    id = fields.UUIDField(pk=True)
    index = fields.IntField()
    theme = fields.TextField(null=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class Classifier(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100)
    storage_path = fields.CharField(max_length=1000)
    activity = fields.ForeignKeyField(model_name="models.Activity", to_field="id")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


async def db_init(db_url=None):
    await Tortoise.init(
        db_url=DB_URI, modules={"models": ["tagmate.models.db.activity"]}
    )
    await Tortoise.generate_schemas()


if __name__ == "__main__":
    run_async(db_init())
