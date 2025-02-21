from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

from django.http import HttpRequest

if TYPE_CHECKING:
    from woo_publications.accounts.models import User

type JSONPrimitive = str | int | float | bool | None
type JSONValue = JSONPrimitive | JSONObject | list[JSONValue]
type JSONObject = dict[str, JSONValue]


class AuthenticatedHttpRequest(HttpRequest):
    user: User  # pyright: ignore[reportIncompatibleVariableOverride]


def is_authenticated_request(
    request: HttpRequest,
) -> TypeGuard[AuthenticatedHttpRequest]:
    return request.user.is_authenticated
