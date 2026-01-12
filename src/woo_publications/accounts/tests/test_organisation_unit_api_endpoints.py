from uuid import uuid4

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.api.tests.mixins import (
    APIKeyUnAuthorizedMixin,
    TokenAuthMixin,
)

from .factories import OrganisationUnitFactory, UserFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class OrganisationUnitApiAuthorizationAndPermissionTests(
    APIKeyUnAuthorizedMixin, APITestCase
):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:organisationunit-list")
        detail_endpoint = reverse(
            "api:organisationunit-detail", kwargs={"identifier": str(uuid4())}
        )

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="put"):
            response = self.client.put(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="patch"):
            response = self.client.patch(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="post"):
            response = self.client.post(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_result_in_301_with_wrong_credentials(self):
        org_unit = OrganisationUnitFactory.create()
        list_url = reverse("api:organisationunit-list")

        detail_url = reverse(
            "api:organisationunit-detail",
            kwargs={"identifier": str(org_unit.identifier)},
        )

        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPutEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPatchEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPostEndpointAccess(list_url)


class OrganisationUnitApiReadTests(TokenAuthMixin, APITestCase):
    def test_list_returns_paginated_response_with_existing_organisation_units(self):
        OrganisationUnitFactory.create_batch(5)
        endpoint = reverse("api:organisationunit-list")

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 5)
        self.assertIn("results", data)

    def test_retrieve_organisation_unit(self):
        organisation_unit = OrganisationUnitFactory.create(
            naam="VTH", identifier="org-unit-42"
        )
        endpoint = reverse(
            "api:organisationunit-detail",
            kwargs={"identifier": organisation_unit.identifier},
        )

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "identifier": "org-unit-42",
                "naam": "VTH",
            },
        )


class OrganisationUnitApiWriteTests(TokenAuthMixin, APITestCase):
    def test_cannot_create_resources(self):
        """
        Assert that creation of organisation units is prohibited.
        """
        endpoint = reverse("api:organisationunit-list")

        response = self.client.post(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_can_update_organisation_unit(self):
        """
        Assert that only the ``naam`` property can be updated.

        ``uuid`` and ``identifier`` are not mutable once a record has been created.
        """
        organisation_unit = OrganisationUnitFactory.create(
            naam="VTH", identifier="org-unit-42"
        )
        original_uuid = organisation_unit.identifier
        endpoint = reverse(
            "api:organisationunit-detail",
            kwargs={"identifier": organisation_unit.identifier},
        )
        body = {
            "identifier": "other-identifier",
            "naam": "Vergunning, toezicht en handhaving",
        }

        response = self.client.patch(endpoint, body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organisation_unit.refresh_from_db()
        self.assertEqual(organisation_unit.identifier, original_uuid)
        self.assertEqual(organisation_unit.identifier, "org-unit-42")
        self.assertEqual(organisation_unit.naam, "Vergunning, toezicht en handhaving")
