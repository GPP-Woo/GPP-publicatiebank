import uuid

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import APIKeyUnAuthorizedMixin, TokenAuthMixin

from .factories import ThemeFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class ThemeAPIAuthorizationAndPermissionTests(APIKeyUnAuthorizedMixin, APITestCase):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:theme-list")
        detail_endpoint = reverse(
            "api:theme-detail", kwargs={"uuid": str(uuid.uuid4())}
        )

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_result_in_401_with_wrong_credentials(self):
        theme = ThemeFactory.create()
        list_url = reverse("api:theme-list")
        detail_url = reverse(
            "api:theme-detail",
            kwargs={"uuid": str(theme.uuid)},
        )

        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)


class ThemeTests(TokenAuthMixin, APITestCase):
    def test_list_theme(self):
        parent_theme = ThemeFactory.create(
            identifier="https://www.example.com/thema/1",
            naam="first item",
        )
        child_theme = ThemeFactory.create(
            identifier="https://www.example.com/thema/2",
            naam="second item",
            parent=parent_theme,
        )
        list_url = reverse("api:theme-list")

        response = self.client.get(list_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)

        expected_second_item_data = {
            "uuid": str(child_theme.uuid),
            "identifier": "https://www.example.com/thema/2",
            "naam": "second item",
            "subThemes": [],
        }

        expected_first_item_data = {
            "uuid": str(parent_theme.uuid),
            "identifier": "https://www.example.com/thema/1",
            "naam": "first item",
            "subThemes": [
                expected_second_item_data,
            ],
        }

        with self.subTest("first item in response with expected_data"):
            self.assertEqual(data["results"][0], expected_first_item_data)

    def test_detail_theme(self):
        theme = ThemeFactory.create(
            identifier="https://www.example.com/thema/1",
            naam="item one",
        )
        list_url = reverse(
            "api:theme-detail",
            kwargs={"uuid": str(theme.uuid)},
        )

        response = self.client.get(list_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        expected_data = {
            "uuid": str(theme.uuid),
            "identifier": "https://www.example.com/thema/1",
            "naam": "item one",
            "subThemes": [],
        }

        self.assertEqual(data, expected_data)

    def test_detail_theme_wrong_uuid(self):
        list_url = reverse(
            "api:theme-detail",
            kwargs={"uuid": uuid.uuid4()},
        )

        response = self.client.get(list_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
