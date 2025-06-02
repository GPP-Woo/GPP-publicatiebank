"""
Test the allowed/blocked publicatiestatus changes for Publicatie and Document.

See https://github.com/GPP-Woo/GPP-publicatiebank/issues/266 for the requirements.
"""

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from woo_publications.api.tests.mixins import (
    APITestCaseMixin,
    TokenAuthMixin,
)
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from .factories import PublicationFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class PublicationStateTransitionAPITests(TokenAuthMixin, APITestCaseMixin, APITestCase):
    """
    Test the publicatiestatus transition behaviour in the API.
    """

    def test_publication_creation(self):
        """
        Assert that a publication can be created with an initial status.
        """
        endpoint = reverse("api:publication-list")
        information_category = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        base = {
            "informatieCategorieen": [str(information_category.uuid)],
            "publisher": str(organisation.uuid),
            "verantwoordelijke": str(organisation.uuid),
            "opsteller": str(organisation.uuid),
            "officieleTitel": "Test",
        }

        with self.subTest("no explicit status"):
            response = self.client.post(endpoint, base, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(
                response.json()["publicatiestatus"], PublicationStatusOptions.published
            )

        with self.subTest("initial status: concept"):
            body = {**base, "publicatiestatus": PublicationStatusOptions.concept}

            response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(
                response.json()["publicatiestatus"], PublicationStatusOptions.concept
            )

        with self.subTest("initial status: published"):
            body = {**base, "publicatiestatus": PublicationStatusOptions.published}

            response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(
                response.json()["publicatiestatus"], PublicationStatusOptions.published
            )

        with self.subTest("blocked status: revoked"):
            body = {**base, "publicatiestatus": PublicationStatusOptions.revoked}

            response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

    def test_concept_publication(self):
        """
        Test the valid state transitions for a concept publication.
        """
        information_category = InformationCategoryFactory.create()

        with self.subTest("publish"):
            publication1 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.concept,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication1.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            publication1.refresh_from_db()
            self.assertEqual(
                publication1.publicatiestatus, PublicationStatusOptions.published
            )

        with self.subTest("revoke (blocked)"):
            publication2 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.concept,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication2.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

        # updating with the same status must be possible (since other metadata fields
        # can change)
        with self.subTest("identity 'update'"):
            publication3 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.concept,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication3.uuid}
            )
            body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

            response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_published_publication(self):
        """
        Test the valid state transitions for a published publication.
        """
        information_category = InformationCategoryFactory.create()

        with self.subTest("revoke"):
            publication1 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication1.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            publication1.refresh_from_db()
            self.assertEqual(
                publication1.publicatiestatus, PublicationStatusOptions.revoked
            )

        with self.subTest("concept (blocked)"):
            publication2 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication2.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.concept},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

        # updating with the same status must be possible (since other metadata fields
        # can change)
        with self.subTest("identity 'update'"):
            publication3 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication3.uuid}
            )
            body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

            response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_revoked_publication(self):
        """
        Test the valid state transitions for a revoked publication.
        """
        information_category = InformationCategoryFactory.create()

        with self.subTest("concept (blocked)"):
            publication1 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.revoked,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication1.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.concept},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

        with self.subTest("published (blocked)"):
            publication2 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.revoked,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication2.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

        # updating with the same status must be possible (since other metadata fields
        # can change)
        with self.subTest("identity 'update'"):
            publication3 = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.revoked,
                informatie_categorieen=[information_category],
            )
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication3.uuid}
            )
            body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

            response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
