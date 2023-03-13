from os import getenv as env
from arq.connections import RedisSettings
from httpx import AsyncClient

from tagmate.classifiers.entity_classification import EntityClassifier
from tagmate.classifiers.multi_label_classification import MultiLabelClassifier
from tagmate.logging.worker import LOG_LEVEL, BASELOGFMT, DATEFMT, JobLogger
import logging

logger = logging.getLogger("arq")


JOB_TIMEOUT = 60 * 60 * 30  # 3 hours


async def startup(ctx):
    ctx["session"] = AsyncClient()


async def shutdown(ctx):
    await ctx["session"].aclose()


async def train_multilabel_classifier(ctx, activity_id: int, metadata: dict = {}):
    job_logger = JobLogger(job_id=ctx["job_id"])
    classifier = MultiLabelClassifier(
        activity_id=activity_id,
        logger=job_logger,
    )
    response = await classifier.train_classifier()
    return response


async def train_entity_classifier(ctx, activity_id: int, metadata: dict = {}):
    classifier = EntityClassifier(
        activity_id=activity_id,
    )
    response = await classifier.train_classifier()
    return response


class WorkerSettings:
    functions = [train_multilabel_classifier, train_entity_classifier]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(host=env("REDIS_HOST"), port=env("REDIS_PORT"))
    job_timeout = JOB_TIMEOUT
    allow_abort_jobs = True


LoggerSettings = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "standard": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "formatters": {"standard": {"format": BASELOGFMT, "datefmt": DATEFMT}},
    "loggers": {
        "arq": {"handlers": ["standard"], "level": LOG_LEVEL},
    },
}
