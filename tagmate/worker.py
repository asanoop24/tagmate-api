from os import getenv as env
from arq.connections import RedisSettings
from httpx import AsyncClient

from tagmate.classifiers.entity_classification import EntityClassifier
from tagmate.classifiers.multi_label_classification import MultiLabelClassifier
from tagmate.classifiers.clustering import ClusterBuilder
from tagmate.models.enums import ActivityTaskEnum, JobStatusEnum
from tagmate.logging.worker import LOG_LEVEL, BASELOGFMT, DATEFMT, JobLogger
from tagmate.utils.database import db_init
from tagmate.models.db.activity import Job as JobTable
import logging

logger = logging.getLogger("arq")


JOB_TIMEOUT = 60 * 60 * 30  # 3 hours


async def startup(ctx):
    ctx["session"] = AsyncClient()


async def shutdown(ctx):
    await ctx["session"].aclose()


async def update_job_status(id: str, status: str | JobStatusEnum):
    await db_init()
    await JobTable(id=id, status=status).save(update_fields=["status", "updated_at"])


async def multi_label_classification(ctx, activity_id: int, metadata: dict = {}):
    job_id = ctx.get("job_id")
    job_logger = JobLogger(job_id=job_id)

    classifier = MultiLabelClassifier(
        activity_id=activity_id,
        logger=job_logger,
    )
    try:
        await classifier.train_classifier()
        await update_job_status(job_id, JobStatusEnum.success)
    except Exception as exc:
        await update_job_status(job_id, JobStatusEnum.failed)
        raise


async def entity_classification(ctx, activity_id: int, metadata: dict = {}):
    job_id = ctx.get("job_id")
    job_logger = JobLogger(job_id=job_id)
    classifier = EntityClassifier(
        activity_id=activity_id,
    )
    response = await classifier.train_classifier()
    return response


async def clustering(ctx, activity_id: int):
    job_id = ctx.get("job_id")
    job_logger = JobLogger(job_id=job_id)
    builder = ClusterBuilder(
        activity_id=activity_id,
        logger=job_logger,
    )
    response = await builder.run_clustering()
    return response


class WorkerSettings:
    functions = [clustering, multi_label_classification, entity_classification]
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
