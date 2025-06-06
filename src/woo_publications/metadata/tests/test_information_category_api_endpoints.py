import uuid

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import APIKeyUnAuthorizedMixin, TokenAuthMixin

from ..constants import InformationCategoryOrigins
from .factories import InformationCategoryFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class InformationCategoryAPIAuthorizationAndPermissionTests(
    APIKeyUnAuthorizedMixin, APITestCase
):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:informationcategory-list")
        detail_endpoint = reverse(
            "api:informationcategory-detail", kwargs={"uuid": str(uuid.uuid4())}
        )

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_result_in_401_with_wrong_credentials(self):
        information_category = InformationCategoryFactory.create()
        list_url = reverse("api:informationcategory-list")
        detail_url = reverse(
            "api:informationcategory-detail",
            kwargs={"uuid": str(information_category.uuid)},
        )

        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)


class InformationCategoryTests(TokenAuthMixin, APITestCase):
    def test_list_informatie_categorie(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            naam_meervoud="first items",
            definitie="This is some information about the first item.",
            order=0,
            oorsprong=InformationCategoryOrigins.value_list,
        )
        information_category2 = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            naam_meervoud="second items",
            omschrijving="bla bla bla",
            definitie="This is some information about the second item.",
            order=1,
            oorsprong=InformationCategoryOrigins.custom_entry,
        )

        list_url = reverse("api:informationcategory-list")

        response = self.client.get(list_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

        with self.subTest("first item in response with expected_data"):
            expected_first_item_data = {
                "uuid": str(information_category.uuid),
                "identifier": "https://www.example.com/waardenlijsten/1",
                "naam": "first item",
                "naamMeervoud": "first items",
                "omschrijving": "",
                "definitie": "This is some information about the first item.",
                "order": 0,
                "oorsprong": InformationCategoryOrigins.value_list,
            }
            self.assertEqual(data["results"][0], expected_first_item_data)

        with self.subTest("second item in response with expected_data"):
            expected_second_item_data = {
                "uuid": str(information_category2.uuid),
                "identifier": "https://www.example.com/waardenlijsten/2",
                "naam": "second item",
                "naamMeervoud": "second items",
                "omschrijving": "bla bla bla",
                "definitie": "This is some information about the second item.",
                "order": 1,
                "oorsprong": InformationCategoryOrigins.custom_entry,
            }
            self.assertEqual(data["results"][1], expected_second_item_data)

    def test_list_informatie_categorie_search_on_identifier(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            naam_meervoud="first items",
            definitie="This is some information about the first item.",
            order=0,
            oorsprong=InformationCategoryOrigins.value_list,
        )
        InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            naam_meervoud="second items",
            definitie="This is some information about the second item.",
            order=1,
            oorsprong=InformationCategoryOrigins.custom_entry,
        )

        list_url = reverse("api:informationcategory-list")

        expected_first_item_data = {
            "uuid": str(information_category.uuid),
            "identifier": "https://www.example.com/waardenlijsten/1",
            "naam": "first item",
            "naamMeervoud": "first items",
            "omschrijving": "",
            "definitie": "This is some information about the first item.",
            "order": 0,
            "oorsprong": InformationCategoryOrigins.value_list,
        }

        with self.subTest("test with exact match"):
            response = self.client.get(
                list_url,
                {"identifier": "https://www.example.com/waardenlijsten/1"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0], expected_first_item_data)

        with self.subTest("with none existing identifier"):
            response = self.client.get(
                list_url,
                {"identifier": "https://www.example.com/waardenlijsten/999"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)

    def test_list_informatie_categorie_search_on_naam(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="item one",
            naam_meervoud="item one (but plural?)",
            definitie="This is some information about the item one.",
            order=0,
            oorsprong=InformationCategoryOrigins.value_list,
        )
        information_category2 = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="item two",
            naam_meervoud="item two (but plural?)",
            definitie="This is some information about the item two.",
            order=1,
            oorsprong=InformationCategoryOrigins.custom_entry,
        )

        list_url = reverse("api:informationcategory-list")

        expected_item_one_data = {
            "uuid": str(information_category.uuid),
            "identifier": "https://www.example.com/waardenlijsten/1",
            "naam": "item one",
            "naamMeervoud": "item one (but plural?)",
            "omschrijving": "",
            "definitie": "This is some information about the item one.",
            "order": 0,
            "oorsprong": InformationCategoryOrigins.value_list,
        }
        expected_item_two_data = {
            "uuid": str(information_category2.uuid),
            "identifier": "https://www.example.com/waardenlijsten/2",
            "naam": "item two",
            "naamMeervoud": "item two (but plural?)",
            "omschrijving": "",
            "definitie": "This is some information about the item two.",
            "order": 1,
            "oorsprong": InformationCategoryOrigins.custom_entry,
        }

        with self.subTest("test with exact match"):
            response = self.client.get(
                list_url, {"naam": "item two"}, headers=AUDIT_HEADERS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0], expected_item_two_data)

        with self.subTest("test with incomplete match"):
            response = self.client.get(
                list_url, {"naam": "item"}, headers=AUDIT_HEADERS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0], expected_item_one_data)
            self.assertEqual(data["results"][1], expected_item_two_data)

        with self.subTest("with none existing identifier"):
            response = self.client.get(
                list_url, {"naam": "item three"}, headers=AUDIT_HEADERS
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)

    def test_detail_informatie_categorie(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            naam_meervoud="first items",
            omschrijving="bla bla bla",
            definitie="This is some information about the first item.",
            order=0,
            oorsprong=InformationCategoryOrigins.value_list,
        )
        detail_url = reverse(
            "api:informationcategory-detail",
            kwargs={"uuid": str(information_category.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        expected_data = {
            "uuid": str(information_category.uuid),
            "identifier": "https://www.example.com/waardenlijsten/1",
            "naam": "first item",
            "naamMeervoud": "first items",
            "omschrijving": "bla bla bla",
            "definitie": "This is some information about the first item.",
            "order": 0,
            "oorsprong": InformationCategoryOrigins.value_list,
        }
        self.assertEqual(data, expected_data)
