from tortoise import Tortoise, fields, run_async
from tortoise.contrib.postgres.fields import ArrayField
from tortoise.models import Model

from tagmate.utils.database import DB_URI


class Activity(Model):  # type: ignore
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100)
    task = fields.CharField(max_length=100)
    file_name = fields.CharField(max_length=1000)
    tags = ArrayField(element_type="text", null=True)
    user = fields.ForeignKeyField(model_name="models.User", to_field="id")
    storage_path = fields.CharField(max_length=1000)
    created_at = fields.DatetimeField(auto_now_add=True)


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
    labels = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


async def db_init(db_url=None):
    await Tortoise.init(
        db_url=DB_URI, modules={"models": ["tagmate.models.db.activity"]}
    )
    await Tortoise.generate_schemas()


if __name__ == "__main__":
    run_async(db_init())
