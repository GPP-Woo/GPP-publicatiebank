import structlog
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = structlog.stdlib.get_logger(__name__)


def exception_handler(exc: Exception, context) -> Response | None:
    if isinstance(exc, exceptions.ValidationError):
        logger.info("invalid_input_received", problems=exc.get_full_details())
    return drf_exception_handler(exc, context)
