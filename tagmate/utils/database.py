from os import getenv as env
from tortoise import Tortoise, run_async

PG_USERNAME = env("POSTGRES_USER", "postgres")
PG_PASSWORD = env("POSTGRES_PASSWORD", "postgres")
PG_HOST = env("POSTGRES_HOST", "postgres")
PG_PORT = env("POSTGRES_PORT", 5432)
PG_DATABASE = "postgres"

DB_URI = f"postgres://{PG_USERNAME}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
DB_MODELS = ["tagmate.models.db.activity", "tagmate.models.db.user"]


async def db_init(db_url=None):
    await Tortoise.init(
        db_url=DB_URI,
        modules={"models": DB_MODELS},
    )


if __name__ == "__main__":
    run_async(db_init())
