from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException


class BadGateway(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = _("Bad gateway.")
