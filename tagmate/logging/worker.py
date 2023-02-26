import logging
from os import getenv as env
import sys


LOG_LEVEL = logging.getLevelName(env("APP_LOG_LEVEL", "INFO"))
SEP = " "*4
BASELOGFMT = f"[time] %(asctime)s.%(msecs)03d{SEP}[level] %(levelname)-8s [logger] %(name)-10s{SEP}[message] %(message)s"
JOBLOGFMT = f"[time] %(asctime)s.%(msecs)03d{SEP}[level] %(levelname)-8s [logger] %(name)-10s{SEP}[requestID] %(requestID)s{SEP}[jobID] %(jobID)s{SEP}[message] %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"

JOB_LOGGER_NAME = "tagmate.worker.job"

ENABLE_LOGGERS = [
    # "root",
    "tortoise",
    "tortoise.db_client",
    "minio",
    "sentence_transformers.SentenceTransformer",
]

stdout = logging.StreamHandler(sys.stdout)
for module in ENABLE_LOGGERS:
    stdout.setFormatter(logging.Formatter(fmt=BASELOGFMT, datefmt=DATEFMT))
    logging.getLogger(module).setLevel(LOG_LEVEL)
    logging.getLogger(module).addHandler(stdout)


class JobLogger(logging.LoggerAdapter):

    def __init__(self, job_id: str = "0", request_id: str = "0"):
        self.job_id = job_id
        self.request_id = request_id
        self.level = LOG_LEVEL
        self.extra = {
            "jobID": self.job_id,
            "requestID": self.request_id,
        }

        self.logger = logging.Logger(JOB_LOGGER_NAME)

        # ensure the logger is not disabled for the desired level
        self.logger.disabled = False
        self.logger.isEnabledFor(LOG_LEVEL)
        self.logger.setLevel(LOG_LEVEL)

        self.handler = logging.StreamHandler(sys.stdout)
        self.handler.setFormatter(logging.Formatter(fmt=JOBLOGFMT, datefmt=DATEFMT))
        self.logger.handlers = [self.handler]

        super().__init__(self.logger, self.extra)


logger = logging.getLogger()