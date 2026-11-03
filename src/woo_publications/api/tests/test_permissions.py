import datetime

from django.urls import path

from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.test import (
    APIRequestFactory,
    APISimpleTestCase,
    APITestCase,
    URLPatternsTestCase,
)

from ..authorization import TokenAuthentication
from ..drf_spectacular.headers import ALL_AUDIT_PARAMETERS
from ..permissions import AuditHeaderPermission, TokenAuthPermission
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


class TestAutorizationAndPermissionView(views.APIView):
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


class ApiTokenAuthorizationAndPermissionTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("whatever", TestAutorizationAndPermissionView.as_view()),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.no_permission_token = TokenAuthFactory.create(permissions=[]).token
        cls.read_token = TokenAuthFactory.create(read_permission=True).token
        cls.write_token = TokenAuthFactory.create(write_permission=True).token
        cls.read_write_token = TokenAuthFactory.create(read_write_permission=True).token
        cls.expired_token = TokenAuthFactory.create(
            read_write_permission=True, expire_date=datetime.date(1970, 1, 1)
        ).token

    def test_get_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.get("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.get(
                "/whatever", headers={"Authorization": "Token broken"}
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("token with no permission"):
            response = self.client.get(
                "/whatever",
                headers={"Authorization": f"Token {self.no_permission_token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with wrong permission"):
            response = self.client.get(
                "/whatever", headers={"Authorization": f"Token {self.write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with expired date"):
            response = self.client.get(
                "/whatever", headers={"Authorization": f"Token {self.expired_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with correct permission"):
            response = self.client.get(
                "/whatever", headers={"Authorization": f"Token {self.read_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("token with all permissions"):
            response = self.client.get(
                "/whatever", headers={"Authorization": f"Token {self.read_write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.post("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.post(
                "/whatever", headers={"Authorization": "Token broken"}
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("token with no permission"):
            response = self.client.post(
                "/whatever",
                headers={"Authorization": f"Token {self.no_permission_token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with wrong permission"):
            response = self.client.post(
                "/whatever", headers={"Authorization": f"Token {self.read_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with expired date"):
            response = self.client.post(
                "/whatever", headers={"Authorization": f"Token {self.expired_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with correct permission"):
            response = self.client.post(
                "/whatever", headers={"Authorization": f"Token {self.write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("token with all permissions"):
            response = self.client.post(
                "/whatever", headers={"Authorization": f"Token {self.read_write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_put_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.put("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.put(
                "/whatever", headers={"Authorization": "Token broken"}
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("token with no permission"):
            response = self.client.put(
                "/whatever",
                headers={"Authorization": f"Token {self.no_permission_token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with wrong permission"):
            response = self.client.put(
                "/whatever", headers={"Authorization": f"Token {self.read_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with expired date"):
            response = self.client.put(
                "/whatever", headers={"Authorization": f"Token {self.expired_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with correct permission"):
            response = self.client.put(
                "/whatever", headers={"Authorization": f"Token {self.write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("token with all permissions"):
            response = self.client.put(
                "/whatever", headers={"Authorization": f"Token {self.read_write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_endpoint(self):
        with self.subTest("no token given"):
            response = self.client.delete("/whatever")
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("none existing token"):
            response = self.client.delete(
                "/whatever", headers={"Authorization": "Token broken"}
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        with self.subTest("token with no permission"):
            response = self.client.delete(
                "/whatever",
                headers={"Authorization": f"Token {self.no_permission_token}"},
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with wrong permission"):
            response = self.client.delete(
                "/whatever", headers={"Authorization": f"Token {self.read_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with expired date"):
            response = self.client.delete(
                "/whatever", headers={"Authorization": f"Token {self.expired_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("token with correct permission"):
            response = self.client.delete(
                "/whatever", headers={"Authorization": f"Token {self.write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.subTest("token with all permissions"):
            response = self.client.delete(
                "/whatever", headers={"Authorization": f"Token {self.read_write_token}"}
            )
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
