import datetime
import itertools
from collections.abc import Iterable
from itertools import chain, combinations, product
from typing import assert_never
from zoneinfo import ZoneInfo

from django.test import override_settings
from django.urls import path

from freezegun.api import freeze_time
from parametrize.parametrize import parametrize
from rest_framework import status, views
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.test import (
    APIRequestFactory,
    APISimpleTestCase,
    APITestCase,
    URLPatternsTestCase,
)

from ..authorization import TokenAuthentication
from ..constants import ApiOptions, PermissionOptions
from ..drf_spectacular.headers import ALL_AUDIT_PARAMETERS
from ..permissions import (
    ApplicationTokenAuthPermission,
    AuditHeaderPermission,
    ReuseTokenAuthPermission,
    TokenAuthPermission,
)
from .factories import TokenAuthFactory

request_factory = APIRequestFactory()


class AuditHeadersPermissionTests(APISimpleTestCase):
    def test_api_call_with_all_audit_headers_passes(self):
        request = request_factory.get(
            "/irrelevant",
            headers={
                "Audit-User-Representation": "test",
                "Audit-User-ID": "test",
                "Audit-Remarks": "test",
            },
        )
        view = views.APIView()
        permission = AuditHeaderPermission()

        result = permission.has_permission(request, view)

        self.assertTrue(result)

    def test_api_call_with_one_audit_header_results_in_403(self):
        for single_header in [
            header.name for header in ALL_AUDIT_PARAMETERS if header.required
        ]:
            with self.subTest(header=single_header):
                request = request_factory.get(
                    "/irrelevant", headers={single_header: "test"}
                )
                view = views.APIView()
                permission = AuditHeaderPermission()

                result = permission.has_permission(request, view)

                self.assertFalse(result)

    def test_api_call_with_no_audit_header_results_in_403(self):
        request = request_factory.get("/irrelevant")
        view = views.APIView()
        permission = AuditHeaderPermission()

        result = permission.has_permission(request, view)

        self.assertFalse(result)


class BaseTestAutorizationAndPermissionView(views.APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (TokenAuthPermission,)

    """
    A simple ViewSet for listing or retrieving users.
    """

    def get(self, request):
        return Response(status=status.HTTP_200_OK)

    def post(self, request):
        return Response(status=status.HTTP_201_CREATED)

    def put(self, request, pk=None):
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, pk=None):
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationTestAuthorizationAndPermissionView(
    BaseTestAutorizationAndPermissionView
):
    permission_classes = (ApplicationTokenAuthPermission,)


class ReuseTestAuthorizationAndPermissionView(BaseTestAutorizationAndPermissionView):
    permission_classes = (ReuseTokenAuthPermission,)


@override_settings(LANGUAGE_CODE="en")
class ApiTokenAuthorizationAndPermissionTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("whatever", ApplicationTestAuthorizationAndPermissionView.as_view()),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.no_permission_token = TokenAuthFactory.create(permissions=[]).raw_token
        cls.read_token = TokenAuthFactory.create(read_permission=True).raw_token
        cls.write_token = TokenAuthFactory.create(write_permission=True).raw_token
        cls.read_write_token = TokenAuthFactory.create(
            read_write_permission=True
        ).raw_token
        cls.expired_token = TokenAuthFactory.create(
            read_write_permission=True, expire_date=datetime.date(1970, 1, 1)
        ).raw_token

    def test_get_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.get("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertEqual(
                response.json()["detail"],
                "Authentication credentials were not provided.",
            )


def subsets[T](items: Iterable[T]) -> list[list[T]]:
    elements = list(items)
    return [
        list(subset)
        for subset in chain.from_iterable(
            combinations(elements, n) for n in range(len(elements) + 1)
        )
    ]


class TokenAuthPermissionTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path(
            "test_application", ApplicationTestAuthorizationAndPermissionView.as_view()
        ),
        path("test_reuse", ReuseTestAuthorizationAndPermissionView.as_view()),
    ]

    @parametrize(
        "api_access,permissions,api,method",
        list(
            product(
                subsets(ApiOptions),
                subsets(PermissionOptions),
                ApiOptions,
                ["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
            )
        ),
    )
    def test_has_permission(
        self,
        api_access: list[ApiOptions],
        permissions: list[PermissionOptions],
        api: ApiOptions,
        method: str,
    ):
        match api:
            case ApiOptions.application:
                permission_class = (
                    ApplicationTestAuthorizationAndPermissionView.permission_classes[0]
                )
                permission_view = ApplicationTestAuthorizationAndPermissionView
                url = "test_application"
            case ApiOptions.reuse:
                permission_class = (
                    ReuseTestAuthorizationAndPermissionView.permission_classes[0]
                )
                permission_view = ReuseTestAuthorizationAndPermissionView
                url = "test_reuse"
            case _:
                assert_never(api)

        assert permission_class
        assert permission_view

        token = TokenAuthFactory.build(api_access=api_access, permissions=permissions)
        request = request_factory.generic(method, url)
        request.auth = token
        permission = (
            PermissionOptions.read
            if method in SAFE_METHODS
            else PermissionOptions.write
        )

        result = permission_class().has_permission(
            request=request,
            view=permission_view,  # pyright: ignore[reportArgumentType]
        )

        self.assertEqual(result, api in api_access and permission in permissions)

    @parametrize(
        "action,url",
        list(
            product(
                ["get", "post", "put", "patch", "delete"],
                ["test_application", "test_reuse"],
            )
        ),
    )
    def test_fake_token_has_no_access(self, action, url):
        with self.subTest("application access with read permission"):
            self.client.request()
            request = getattr(self.client, action)
            response = request(
                "/test_reuse",
                headers={"Authorization": "Token does-not-exist"},
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(LANGUAGE_CODE="en")
class TokenExpiryBoundaryTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("whatever", ApplicationTestAuthorizationAndPermissionView.as_view())
    ]
    AMSTERDAM = ZoneInfo("Europe/Amsterdam")
    D = datetime.date(2026, 11, 6)
    DAY = datetime.timedelta(days=1)

    def test_expiry_is_judged_by_the_local_date(self):
        expire_dates = (None, self.D - self.DAY, self.D, self.D + self.DAY)
        instants = (
            datetime.datetime(2026, 11, 5, 23, 30, tzinfo=self.AMSTERDAM),
            datetime.datetime(
                2026, 11, 6, 0, 30, tzinfo=self.AMSTERDAM
            ),  # 23:30 UTC on d-1
            datetime.datetime(2026, 11, 6, 23, 30, tzinfo=self.AMSTERDAM),
        )

        for expire_date, now in itertools.product(expire_dates, instants):
            with self.subTest(expire_date=expire_date, now=now.isoformat()):
                token = TokenAuthFactory.create(
                    read_permission=True, full_api_access=True, expire_date=expire_date
                ).raw_token
                # oracle: the calendar date on an Amsterdam wall clock
                accepted = expire_date is None or expire_date > now.date()

                with freeze_time(now):
                    response = self.client.get(
                        "/whatever", headers={"Authorization": f"Token {token}"}
                    )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK if accepted else status.HTTP_401_UNAUTHORIZED,
                )
