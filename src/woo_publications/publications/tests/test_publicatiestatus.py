"""
Test the allowed/blocked publicatiestatus changes for Publicatie and Document.

See https://github.com/GPP-Woo/GPP-publicatiebank/issues/266 for the requirements.
"""

from unittest.mock import MagicMock, patch

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
from .factories import DocumentFactory, PublicationFactory

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

    @patch("woo_publications.publications.tasks.index_publication.delay")
    @patch("woo_publications.publications.tasks.index_document.delay")
    def test_publish_cascades_to_documents(
        self,
        mock_index_document: MagicMock,
        mock_index_publication: MagicMock,
    ):
        """
        Assert that related documents get published together with the publication.
        """
        information_category = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[information_category],
            publicatiestatus=PublicationStatusOptions.concept,
        )
        document = DocumentFactory.create(
            publicatie=publication,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        endpoint = reverse("api:publication-detail", kwargs={"uuid": publication.uuid})

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.published)
        mock_index_publication.assert_called_once_with(publication_id=publication.pk)


class DocumentStateTransitionAPITests(TokenAuthMixin, APITestCaseMixin, APITestCase):
    """
    Test the publicatiestatus transition behaviour in the API.
    """

    def setUp(self):
        super().setUp()

        # mock out the interaction with the Documents API, it's not relevant for these
        # tests
        patcher = patch(
            "woo_publications.publications.models.Document.register_in_documents_api"
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_create_ignores_publicatiestatus(self):
        """
        Assert that the publicatiestatus field is **ignored** for new documents.

        Instead, the status is derived from the related publication and creawting
        documents in a revoked publication must not be possible at all.
        """
        information_category = InformationCategoryFactory.create()
        endpoint = reverse("api:document-list")
        base = {
            "officieleTitel": "Test",
            "creatiedatum": "2024-11-05",
        }

        with self.subTest("concept publication"):
            concept_publication = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.concept,
                informatie_categorieen=[information_category],
            )

            for _status in PublicationStatusOptions:
                with self.subTest(request_body_publicatiestatus=_status):
                    body = {
                        **base,
                        "publicatie": concept_publication.uuid,
                        "publicatiestatus": _status,
                    }

                    response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    self.assertEqual(
                        response.json()["publicatiestatus"],
                        PublicationStatusOptions.concept,
                    )

        with self.subTest("published publication"):
            published_publication = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                informatie_categorieen=[information_category],
            )

            for _status in PublicationStatusOptions:
                with self.subTest(request_body_publicatiestatus=_status):
                    body = {
                        **base,
                        "publicatie": published_publication.uuid,
                        "publicatiestatus": _status,
                    }

                    response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

                    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                    self.assertEqual(
                        response.json()["publicatiestatus"],
                        PublicationStatusOptions.published,
                    )

        with self.subTest("revoked publication"):
            revoked_publication = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.revoked,
                informatie_categorieen=[information_category],
            )

            for _status in PublicationStatusOptions:
                with self.subTest(request_body_publicatiestatus=_status):
                    body = {
                        **base,
                        "publicatie": revoked_publication.uuid,
                        "publicatiestatus": _status,
                    }

                    response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(list(response.data.keys()), ["non_field_errors"])

    def test_concept_document(self):
        """
        Assert that the status cannot be set via the API.

        Concept documents can only occur within concept publications.
        """
        information_category = InformationCategoryFactory.create()
        concept_document = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.concept,
            publicatie__informatie_categorieen=[information_category],
            publicatiestatus=PublicationStatusOptions.concept,
        )
        endpoint = reverse(
            "api:document-detail", kwargs={"uuid": concept_document.uuid}
        )

        with self.subTest("publish (blocked)"):
            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

        with self.subTest("revoke (blocked)"):
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
            body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

            response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_published_document(self):
        """
        Check the valid state transitions for published documents.

        Published documents can only occur within published publications.
        """
        information_category = InformationCategoryFactory.create()

        with self.subTest("concept (blocked)"):
            published_document1 = DocumentFactory.create(
                publicatie__publicatiestatus=PublicationStatusOptions.published,
                publicatie__informatie_categorieen=[information_category],
                publicatiestatus=PublicationStatusOptions.published,
            )
            endpoint = reverse(
                "api:document-detail", kwargs={"uuid": published_document1.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.concept},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

        with self.subTest("revoke"):
            published_document2 = DocumentFactory.create(
                publicatie__publicatiestatus=PublicationStatusOptions.published,
                publicatie__informatie_categorieen=[information_category],
                publicatiestatus=PublicationStatusOptions.published,
            )
            endpoint = reverse(
                "api:document-detail", kwargs={"uuid": published_document2.uuid}
            )

            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json()["publicatiestatus"],
                PublicationStatusOptions.revoked,
            )

        # updating with the same status must be possible (since other metadata fields
        # can change)
        with self.subTest("identity 'update'"):
            published_document3 = DocumentFactory.create(
                publicatie__publicatiestatus=PublicationStatusOptions.published,
                publicatie__informatie_categorieen=[information_category],
                publicatiestatus=PublicationStatusOptions.published,
            )
            endpoint = reverse(
                "api:document-detail", kwargs={"uuid": published_document3.uuid}
            )
            body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

            response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_revoked_document(self):
        """
        Check the valid state transitions for revoked documents.

        Revoked documents can occur within published and revoked publications.
        """
        information_category = InformationCategoryFactory.create()
        revoked_document1 = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.published,
            publicatie__informatie_categorieen=[information_category],
            publicatiestatus=PublicationStatusOptions.revoked,
        )
        revoked_document2 = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.revoked,
            publicatie__informatie_categorieen=[information_category],
            publicatiestatus=PublicationStatusOptions.revoked,
        )

        for document in (revoked_document1, revoked_document2):
            document_subtest_kwargs = {
                "publication_status": document.publicatie.publicatiestatus
            }
            endpoint = reverse("api:document-detail", kwargs={"uuid": document.uuid})

            with self.subTest("concept (blocked)", **document_subtest_kwargs):
                response = self.client.patch(
                    endpoint,
                    {"publicatiestatus": PublicationStatusOptions.concept},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

            with self.subTest("published (blocked)", **document_subtest_kwargs):
                response = self.client.patch(
                    endpoint,
                    {"publicatiestatus": PublicationStatusOptions.published},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(list(response.data.keys()), ["publicatiestatus"])

            # updating with the same status must be possible (since other metadata
            # fields can change)
            with self.subTest("identity 'update'", **document_subtest_kwargs):
                body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

                response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
