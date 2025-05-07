from uuid import uuid4

from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import APIKeyUnAuthorizedMixin, TokenAuthMixin

from ..api.filters import OrganisationActive
from ..constants import OrganisationOrigins
from .factories import OrganisationFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class ThemeAPIAuthorizationAndPermissionTests(APIKeyUnAuthorizedMixin, APITestCase):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:organisation-list")
        detail_endpoint = reverse(
            "api:organisation-detail", kwargs={"uuid": str(uuid4())}
        )

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="create"):
            response = self.client.post(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="update"):
            response = self.client.put(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_result_in_401_with_wrong_credentials(self):
        organisation = OrganisationFactory.create()
        list_url = reverse("api:organisation-list")
        detail_url = reverse(
            "api:organisation-detail",
            kwargs={"uuid": str(organisation.uuid)},
        )

        # create
        self.assertWrongApiKeyProhibitsPostEndpointAccess(detail_url)
        # read
        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)
        # update
        self.assertWrongApiKeyProhibitsPatchEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPutEndpointAccess(detail_url)


@override_settings(LANGUAGE_CODE="en")
class OrganisationApiTests(TokenAuthMixin, APITestCase):
    def test_list_organisations(self):
        organisation = OrganisationFactory.create(
            naam="one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        organisation2 = OrganisationFactory.create(
            naam="two",
            identifier="https://www.example.com/organisaties/2",
            is_actief=True,
            oorsprong=OrganisationOrigins.municipality_list,
        )
        expected_first_item_data = {
            "uuid": str(organisation.uuid),
            "identifier": "https://www.example.com/organisaties/1",
            "naam": "one",
            "oorsprong": OrganisationOrigins.custom_entry,
            "isActief": True,
        }
        expected_second_item_data = {
            "uuid": str(organisation2.uuid),
            "identifier": "https://www.example.com/organisaties/2",
            "naam": "two",
            "oorsprong": OrganisationOrigins.municipality_list,
            "isActief": True,
        }

        response = self.client.get(
            reverse("api:organisation-list"), headers=AUDIT_HEADERS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0], expected_first_item_data)
        self.assertEqual(data["results"][1], expected_second_item_data)

    def test_list_organisations_filter_active(self):
        organisation = OrganisationFactory.create(
            naam="one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        organisation2 = OrganisationFactory.create(
            naam="two",
            identifier="https://www.example.com/organisaties/2",
            is_actief=False,
            oorsprong=OrganisationOrigins.municipality_list,
        )

        list_url = reverse("api:organisation-list")

        with self.subTest("default filter on active true"):
            response = self.client.get(list_url, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["identifier"], organisation.identifier)

        with self.subTest("filter on active true"):
            response = self.client.get(
                list_url,
                {"isActief": OrganisationActive.active},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["identifier"], organisation.identifier)

        with self.subTest("filter on active false"):
            response = self.client.get(
                list_url,
                {"isActief": OrganisationActive.inactive},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["identifier"], organisation2.identifier)

        with self.subTest("filter on active every"):
            response = self.client.get(
                list_url,
                {"isActief": OrganisationActive.all},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["identifier"], organisation.identifier)
            self.assertEqual(data["results"][1]["identifier"], organisation2.identifier)

    def test_list_organisations_filter_indentifier(self):
        organisation = OrganisationFactory.create(
            naam="one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        OrganisationFactory.create(
            naam="one",
            identifier="https://www.example.com/organisaties/2",
            is_actief=True,
            oorsprong=OrganisationOrigins.municipality_list,
        )

        list_url = reverse("api:organisation-list")

        with self.subTest("test_with_exact_match"):
            response = self.client.get(
                list_url,
                {"identifier": "https://www.example.com/organisaties/1"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["identifier"], organisation.identifier)

        with self.subTest("with_none_existing_identifier"):
            response = self.client.get(
                list_url,
                {"identifier": "https://www.example.com/organisaties/999"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)

    def test_list_organisations_filter_naam(self):
        organisation = OrganisationFactory.create(
            naam="object one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        organisation2 = OrganisationFactory.create(
            naam="object two",
            identifier="https://www.example.com/organisaties/2",
            is_actief=True,
            oorsprong=OrganisationOrigins.municipality_list,
        )

        list_url = reverse("api:organisation-list")

        with self.subTest("test_with_exact_match"):
            response = self.client.get(
                list_url,
                {"naam": "object two"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["identifier"], organisation2.identifier)

        with self.subTest("test_with_incomplete_match"):
            response = self.client.get(
                list_url,
                {"naam": "object"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["identifier"], organisation.identifier)
            self.assertEqual(data["results"][1]["identifier"], organisation2.identifier)

        with self.subTest("with_none_existing_identifier"):
            response = self.client.get(
                list_url,
                {"naam": "object three"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)

    def test_list_organisations_filter_oorsprong(self):
        OrganisationFactory.create(
            naam="object one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        organisation2 = OrganisationFactory.create(
            naam="object two",
            identifier="https://www.example.com/organisaties/2",
            is_actief=True,
            oorsprong=OrganisationOrigins.municipality_list,
        )
        list_url = reverse("api:organisation-list")

        with self.subTest("test_with_exact_match"):
            response = self.client.get(
                list_url,
                {"oorsprong": OrganisationOrigins.municipality_list},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["identifier"], organisation2.identifier)

        with self.subTest("test_with_incorrect_match"):
            response = self.client.get(
                list_url, {"oorsprong": "test"}, headers=AUDIT_HEADERS
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detail_organisation(self):
        organisation = OrganisationFactory.create(
            naam="object one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        detail_url = reverse(
            "api:organisation-detail",
            kwargs={"uuid": str(organisation.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_data = {
            "uuid": str(organisation.uuid),
            "identifier": "https://www.example.com/organisaties/1",
            "naam": "object one",
            "oorsprong": OrganisationOrigins.custom_entry.value,
            "isActief": True,
        }

        self.assertEqual(data, expected_data)

    def test_create_organisation(self):
        url = reverse("api:organisation-list")
        data = {
            "naam": "object one",
            "isActief": True,
        }

        response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response_data = response.json()
        expected_data = {
            # uuid and identifier gets generated so we are just testing that its there
            "uuid": response_data["uuid"],
            "identifier": response_data["identifier"],
            "naam": "object one",
            "oorsprong": OrganisationOrigins.custom_entry.value,
            "isActief": True,
        }

        self.assertEqual(response_data, expected_data)

    def test_update_organisation(self):
        organisation = OrganisationFactory.create(
            naam="object one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        detail_url = reverse(
            "api:organisation-detail",
            kwargs={"uuid": str(organisation.uuid)},
        )
        data = {
            "naam": "Changed",
            "isActief": False,
        }

        response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        expected_data = {
            # uuid and identifier gets generated so we are just testing that its there
            "uuid": response_data["uuid"],
            "identifier": response_data["identifier"],
            "naam": "Changed",
            "oorsprong": OrganisationOrigins.custom_entry.value,
            "isActief": False,
        }

        self.assertEqual(response_data, expected_data)

    def test_update_organisation_municipality_list_can_only_change_active(self):
        organisation = OrganisationFactory.create(
            naam="object one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.municipality_list,
        )
        detail_url = reverse(
            "api:organisation-detail",
            kwargs={"uuid": str(organisation.uuid)},
        )

        with self.subTest("test update is actief"):
            response = self.client.put(
                detail_url,
                {"isActief": False},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()
            expected_data = {
                # uuid and identifier gets generated so we are just testing that its
                # there
                "uuid": response_data["uuid"],
                "identifier": response_data["identifier"],
                "naam": "object one",
                "oorsprong": OrganisationOrigins.municipality_list.value,
                "isActief": False,
            }

            self.assertEqual(response_data, expected_data)

        with self.subTest("test update name results in 400"):
            response = self.client.put(
                detail_url,
                {"naam": "error"},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_data = response.json()
            self.assertEqual(
                response_data["naam"],
                [
                    "You cannot modify the name of organisations populated from a "
                    "value list."
                ],
            )

    def test_partial_update_organisation(self):
        organisation = OrganisationFactory.create(
            naam="object one",
            identifier="https://www.example.com/organisaties/1",
            is_actief=True,
            oorsprong=OrganisationOrigins.custom_entry,
        )
        detail_url = reverse(
            "api:organisation-detail",
            kwargs={"uuid": str(organisation.uuid)},
        )

        response = self.client.patch(
            detail_url, {"isActief": False}, headers=AUDIT_HEADERS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        expected_data = {
            # uuid and identifier gets generated so we are just testing that its there
            "uuid": response_data["uuid"],
            "identifier": response_data["identifier"],
            "naam": "object one",
            "oorsprong": OrganisationOrigins.custom_entry.value,
            "isActief": False,
        }

        self.assertEqual(response_data, expected_data)
