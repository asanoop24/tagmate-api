import logging
from os import getenv as env
import sys


LOG_LEVEL = logging.getLevelName(env("APP_LOG_LEVEL", "INFO"))
SEP = " " * 2

BASELOGFMT = f"[time] %(asctime)s.%(msecs)03d{SEP}[level] %(levelname)-6s [logger] %(name)-10s{SEP}[requestID] %(requestID)s{SEP}[message] %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"

ENABLE_LOGGERS = [
    *logging.root.manager.loggerDict.keys(),
    "root",
    "tagmate",
    "tortoise",
    "tortoise.db_client",
    "minio",
    "gunicorn",
    "gunicorn.access",
    "gunicorn.error",
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
]

FILTER_ROUTES = [
    "GET /metrics HTTP/",
    "GET /api/v1/healthz HTTP/",
]


class RouteFilter(logging.Filter):
    def filter(self, record):
        if LOG_LEVEL == logging.DEBUG:
            return True

        message = record.getMessage()
        if any([route in message for route in FILTER_ROUTES]):
            return False

        return True


class BaseHandler(logging.StreamHandler):
    def format(self, record):
        try:
            record.requestID
        except:
            record.requestID = "0"

        fmt = logging.Formatter(fmt=BASELOGFMT, datefmt=DATEFMT)
        return fmt.format(record)


def init_logger():
    stdout = BaseHandler(sys.stdout)
    for module in ENABLE_LOGGERS:
        stdout.setFormatter(logging.Formatter(fmt=BASELOGFMT, datefmt=DATEFMT))
        logging.getLogger(module).disabled = False
        logging.getLogger(module).isEnabledFor(logging.INFO)
        logging.getLogger(module).setLevel(LOG_LEVEL)
        for handler in logging.getLogger(module).handlers:
            logging.getLogger(module).removeHandler(handler)
        logging.getLogger(module).addHandler(stdout)
        logging.getLogger(module).addFilter(RouteFilter())


logger = logging.getLogger("tagmate.app")
