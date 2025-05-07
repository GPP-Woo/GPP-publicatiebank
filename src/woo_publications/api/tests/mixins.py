from typing import Any

from rest_framework import status
from rest_framework.test import APIClient

from woo_publications.typing import JSONObject

from .factories import TokenAuthFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class APIKeyUnAuthorizedMixin:
    client: APIClient

    def assertWrongApiKeyProhibitsGetEndpointAccess(self, url):
        no_permission_token = TokenAuthFactory.create(permissions=[]).token
        write_token = TokenAuthFactory.create(write_permission=True).token

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "no token given"
        ):
            response = self.client.get(url, headers=AUDIT_HEADERS)
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "none existing token"
        ):
            response = self.client.get(
                url, headers={"Authorization": "Token broken", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with no permission"
        ):
            response = self.client.get(
                url,
                headers={
                    "Authorization": f"Token {no_permission_token}",
                    **AUDIT_HEADERS,
                },
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with wrong permission"
        ):
            response = self.client.get(
                url, headers={"Authorization": f"Token {write_token}", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

    def assertWrongApiKeyProhibitsPostEndpointAccess(self, url):
        no_permission_token = TokenAuthFactory.create(permissions=[]).token
        read_token = TokenAuthFactory.create(read_permission=True).token

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "no token given"
        ):
            response = self.client.post(url, headers=AUDIT_HEADERS)
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "none existing token"
        ):
            response = self.client.post(
                url, headers={"Authorization": "Token broken", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with no permission"
        ):
            response = self.client.post(
                url,
                headers={
                    "Authorization": f"Token {no_permission_token}",
                    **AUDIT_HEADERS,
                },
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with wrong permission"
        ):
            response = self.client.post(
                url, headers={"Authorization": f"Token {read_token}", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

    def assertWrongApiKeyProhibitsPatchEndpointAccess(self, url):
        no_permission_token = TokenAuthFactory.create(permissions=[]).token
        read_token = TokenAuthFactory.create(read_permission=True).token

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "no token given"
        ):
            response = self.client.patch(url, headers=AUDIT_HEADERS)
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "none existing token"
        ):
            response = self.client.patch(
                url, headers={"Authorization": "Token broken", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with no permission"
        ):
            response = self.client.patch(
                url,
                headers={
                    "Authorization": f"Token {no_permission_token}",
                    **AUDIT_HEADERS,
                },
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with wrong permission"
        ):
            response = self.client.patch(
                url, headers={"Authorization": f"Token {read_token}", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

    def assertWrongApiKeyProhibitsPutEndpointAccess(self, url):
        no_permission_token = TokenAuthFactory.create(permissions=[]).token
        read_token = TokenAuthFactory.create(read_permission=True).token

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "no token given"
        ):
            response = self.client.put(url, headers=AUDIT_HEADERS)
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "none existing token"
        ):
            response = self.client.put(
                url, headers={"Authorization": "Token broken", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with no permission"
        ):
            response = self.client.put(
                url,
                headers={
                    "Authorization": f"Token {no_permission_token}",
                    **AUDIT_HEADERS,
                },
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with wrong permission"
        ):
            response = self.client.put(
                url, headers={"Authorization": f"Token {read_token}", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

    def assertWrongApiKeyProhibitsDeleteEndpointAccess(self, url):
        no_permission_token = TokenAuthFactory.create(permissions=[]).token
        read_token = TokenAuthFactory.create(read_permission=True).token

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "no token given"
        ):
            response = self.client.delete(url, headers=AUDIT_HEADERS)
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "none existing token"
        ):
            response = self.client.delete(
                url, headers={"Authorization": "Token broken", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with no permission"
        ):
            response = self.client.delete(
                url,
                headers={
                    "Authorization": f"Token {no_permission_token}",
                    **AUDIT_HEADERS,
                },
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )

        with self.subTest(  # pyright: ignore[reportAttributeAccessIssue]
            "token with wrong permission"
        ):
            response = self.client.delete(
                url, headers={"Authorization": f"Token {read_token}", **AUDIT_HEADERS}
            )
            self.assertEqual(  # pyright: ignore[reportAttributeAccessIssue]
                response.status_code, status.HTTP_403_FORBIDDEN
            )


class APITestCaseMixin:
    def assertItemInResults(
        self,
        results: list[JSONObject],
        key: str,
        value: Any,
        count: int | None = None,
    ) -> None:
        """
        Custom assert to validate if value of key is in api results.
        """
        try:
            values: list[Any] = [result[key] for result in results]
        except KeyError as exc:
            raise self.failureException(  # pyright: ignore [reportAttributeAccessIssue]
                f"Key '{key}' not found in the given results."
            ) from exc

        items_found: int = values.count(value)

        if count:
            self.assertEqual(  # pyright: ignore [reportAttributeAccessIssue]
                items_found, count
            )

        else:
            self.assertTrue(  # pyright: ignore [reportAttributeAccessIssue]
                items_found >= 1
            )


class TokenAuthMixin:
    client: APIClient

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # pyright: ignore[reportAttributeAccessIssue]

        cls.token_auth = TokenAuthFactory.create(read_write_permission=True)

    def setUp(self):
        super().setUp()  # pyright: ignore[reportAttributeAccessIssue]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_auth.token}")
