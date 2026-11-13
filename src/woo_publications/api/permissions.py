from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from woo_publications.api.drf_spectacular.headers import ALL_AUDIT_PARAMETERS

from .constants import ApiOptions, PermissionOptions
from .models import Application

if TYPE_CHECKING:
    from rest_framework.views import APIView


class AuditHeaderPermission(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        required_headers = [
            parameter.name for parameter in ALL_AUDIT_PARAMETERS if parameter.required
        ]
        return all(header in request.headers for header in required_headers)


class TokenAuthPermission(BasePermission):
    api_name: ClassVar[ApiOptions]

    def has_permission(self, request, view) -> bool:
        token = request.auth

        if not isinstance(token, Application):
            return False

        assert isinstance(token.permissions, list)
        assert isinstance(token.api_access, list)

        if self.api_name not in token.api_access:
            return False

        if token.expire_date and token.expire_date <= timezone.localdate():
            raise NotAuthenticated(
                detail=_(
                    "The token has expired, please contact support to gain a new one."
                ),
            )

        if (
            request.method in SAFE_METHODS
            and PermissionOptions.read in token.permissions
        ):
            return True

        if (
            request.method not in SAFE_METHODS
            and PermissionOptions.write in token.permissions
        ):
            return True

        return False


class ApplicationTokenAuthPermission(TokenAuthPermission):
    api_name = ApiOptions.application


class ReuseTokenAuthPermission(TokenAuthPermission):
    api_name = ApiOptions.reuse
