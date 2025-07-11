import logging  # noqa: TID251 - correct use to replace stdlib logging
import logging.config  # noqa: TID251 - correct use to replace stdlib logging

import structlog
from celery import Celery
from celery.signals import setup_logging
from django_structlog.celery.steps import DjangoStructLogInitStep

from woo_publications.conf.utils import config

from .setup import setup_env

setup_env()

app = Celery("woo_publications")
app.steps["worker"].add(DjangoStructLogInitStep)
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@setup_logging.connect
def receiver_setup_logging(
    loglevel, logfile, format, colorize, **kwargs
):  # pragma: no cover
    formatter = config("LOG_FORMAT_CONSOLE", default="json")
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                    "foreign_pre_chain": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.stdlib.add_logger_name,
                        structlog.stdlib.add_log_level,
                        structlog.stdlib.ExtraAdder(),
                        structlog.stdlib.PositionalArgumentsFormatter(),
                    ],
                },
                "plain_console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(),
                    "foreign_pre_chain": [
                        structlog.contextvars.merge_contextvars,
                        structlog.processors.TimeStamper(fmt="iso"),
                        structlog.stdlib.add_logger_name,
                        structlog.stdlib.add_log_level,
                        structlog.stdlib.ExtraAdder(),
                        structlog.stdlib.PositionalArgumentsFormatter(),
                    ],
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                },
            },
            "loggers": {
                "woo_publications": {
                    "handlers": ["console"],
                    "level": loglevel,
                },
                "django_structlog": {
                    "handlers": ["console"],
                    "level": loglevel,
                },
            },
        }
    )

    exception_processors = (
        [structlog.processors.format_exc_info] if formatter == "json" else []
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            *exception_processors,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
