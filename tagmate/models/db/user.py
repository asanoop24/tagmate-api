from tortoise.models import Model
from tortoise import fields, run_async, Tortoise

from tagmate.utils.database import DB_URI


class User(Model):  # type: ignore
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100)
    email = fields.CharField(max_length=100, index=True, unique=True)
    password = fields.CharField(max_length=100)
    is_admin = fields.BooleanField()
    created_at = fields.DatetimeField(auto_now_add=True)


async def db_init(db_url=None):
    await Tortoise.init(db_url=DB_URI, modules={"models": ["tagmate.models.db.user"]})
    await Tortoise.generate_schemas()


if __name__ == "__main__":
    run_async(db_init())
