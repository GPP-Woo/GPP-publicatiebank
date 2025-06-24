"""
Test the allowed/blocked publicatiestatus changes for Publicatie and Document.

See https://github.com/GPP-Woo/GPP-publicatiebank/issues/266 for the requirements.
"""

import uuid
from unittest.mock import MagicMock, patch

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.api.tests.mixins import (
    APITestCaseMixin,
    TokenAuthMixin,
)
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from ..models import Document, Publication
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

            with freeze_time("2024-09-25T14:00:00"):
                response = self.client.post(endpoint, body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            data = response.json()
            self.assertEqual(
                data["publicatiestatus"], PublicationStatusOptions.published
            )
            self.assertEqual(data["gepubliceerdOp"], "2024-09-25T16:00:00+02:00")
            self.assertEqual(data["ingetrokkenOp"], None)

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

            with freeze_time("2024-09-25T14:00:00-00:00"):
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
            self.assertEqual(
                str(publication1.gepubliceerd_op), "2024-09-25 14:00:00+00:00"
            )
            self.assertEqual(publication1.ingetrokken_op, None)

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
            self.assertEqual(response.json()["ingetrokkenOp"], None)
            self.assertEqual(response.json()["gepubliceerdOp"], None)

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
            with freeze_time("2026-01-01T00:00:00-00:00"):
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
            self.assertEqual(
                response.json()["gepubliceerdOp"], "2026-01-01T01:00:00+01:00"
            )
            self.assertEqual(response.json()["ingetrokkenOp"], None)

    def test_revoked_publication(self):
        """
        Test the valid state transitions for a revoked publication.
        """
        information_category = InformationCategoryFactory.create()

        with self.subTest("concept (blocked)"):
            publication1 = PublicationFactory.create(
                revoked=True,
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
                revoked=True,
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

    @patch("woo_publications.publications.tasks.index_publication.delay")
    @patch("woo_publications.publications.tasks.index_document.delay")
    def test_publish_side_effects(
        self,
        mock_index_document: MagicMock,
        mock_index_publication: MagicMock,
    ):
        """
        Assert the publication publish action side effects.

        * the publication index background tasks is triggered
        * related documents get published together with the publication
        * the related document index tasks get triggered
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

        with (
            self.captureOnCommitCallbacks(execute=True),
            freeze_time("2024-09-25T14:00:00"),
        ):
            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["gepubliceerdOp"], "2024-09-25T16:00:00+02:00")
        self.assertEqual(response.json()["ingetrokkenOp"], None)
        document.refresh_from_db()
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.published)
        mock_index_publication.assert_called_once_with(publication_id=publication.pk)
        download_path = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )
        mock_index_document.assert_called_once_with(
            document_id=document.pk, download_url=f"http://testserver{download_path}"
        )

    @patch("woo_publications.publications.tasks.remove_publication_from_index.delay")
    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    def test_revoke_side_effects(
        self,
        mock_remove_document_from_index_delay: MagicMock,
        mock_remove_publication_from_index_delay: MagicMock,
    ):
        """
        Assert the publication revoke action side effects.

        * the publication index removal background tasks is triggered
        * related published documents get revoked together with the publication
        * the related document index removal tasks get triggered for published documents
        """
        information_category = InformationCategoryFactory.create()
        with freeze_time("2024-09-25T12:00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[information_category],
                publicatiestatus=PublicationStatusOptions.published,
            )
            published_document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.published,
            )
            revoked_document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.revoked,
            )
        endpoint = reverse("api:publication-detail", kwargs={"uuid": publication.uuid})

        with (
            self.captureOnCommitCallbacks(execute=True),
            freeze_time("2024-09-25T14:00:00"),
        ):
            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["gepubliceerdOp"], "2024-09-25T14:00:00+02:00")
        self.assertEqual(response.json()["ingetrokkenOp"], "2024-09-25T16:00:00+02:00")
        # the already revoked document should not have been touched at all
        original_last_modified_revoked_document = (
            revoked_document.laatst_gewijzigd_datum
        )  # noqa: E501
        revoked_document.refresh_from_db()
        self.assertEqual(
            revoked_document.laatst_gewijzigd_datum,
            original_last_modified_revoked_document,
        )
        published_document.refresh_from_db()
        self.assertEqual(
            published_document.publicatiestatus,
            PublicationStatusOptions.revoked,
        )
        mock_remove_publication_from_index_delay.assert_called_once_with(
            publication_id=publication.pk
        )
        mock_remove_document_from_index_delay.assert_called_once_with(
            document_id=published_document.pk
        )


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

    @freeze_time("2024-09-25T14:00:00")
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
                    data = response.json()
                    self.assertEqual(
                        data["publicatiestatus"],
                        PublicationStatusOptions.concept,
                    )
                    self.assertEqual(data["gepubliceerdOp"], None)
                    self.assertEqual(data["ingetrokkenOp"], None)

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
                    data = response.json()
                    self.assertEqual(
                        data["publicatiestatus"],
                        PublicationStatusOptions.published,
                    )
                    self.assertEqual(
                        data["gepubliceerdOp"], "2024-09-25T16:00:00+02:00"
                    )
                    self.assertEqual(data["ingetrokkenOp"], None)

        with self.subTest("revoked publication"):
            revoked_publication = PublicationFactory.create(
                revoked=True,
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

    @freeze_time("2024-09-25T14:00:00")
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
            data = response.json()
            self.assertEqual(data["gepubliceerdOp"], None)
            self.assertEqual(data["ingetrokkenOp"], None)

    @freeze_time("2024-09-25T14:00:00")
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
            data = response.json()
            self.assertEqual(
                data["publicatiestatus"],
                PublicationStatusOptions.revoked,
            )
            self.assertEqual(data["gepubliceerdOp"], "2024-09-25T16:00:00+02:00")
            self.assertEqual(data["ingetrokkenOp"], "2024-09-25T16:00:00+02:00")

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
            data = response.json()
            self.assertEqual(data["gepubliceerdOp"], "2024-09-25T16:00:00+02:00")
            self.assertEqual(data["ingetrokkenOp"], None)

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
            publicatie__revoked=True,
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

    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    def test_revoke_side_effects(
        self,
        mock_remove_document_from_index_delay: MagicMock,
    ):
        """
        Assert the document revoke action side effects.

        * the document index removal tasks get triggered
        """
        information_category = InformationCategoryFactory.create()
        with freeze_time("2024-09-25T12:00:00"):
            document = DocumentFactory.create(
                publicatie__informatie_categorieen=[information_category],
                publicatie__publicatiestatus=PublicationStatusOptions.published,
                publicatiestatus=PublicationStatusOptions.published,
            )
        endpoint = reverse("api:document-detail", kwargs={"uuid": document.uuid})

        with (
            self.captureOnCommitCallbacks(execute=True),
            freeze_time("2024-09-25T14:00:00"),
        ):
            response = self.client.patch(
                endpoint,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(response.json()["gepubliceerdOp"], "2024-09-25T14:00:00+02:00")
        self.assertEqual(response.json()["ingetrokkenOp"], "2024-09-25T16:00:00+02:00")
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.revoked)
        mock_remove_document_from_index_delay.assert_called_once_with(
            document_id=document.pk
        )


@disable_admin_mfa()
@freeze_time("2024-09-25T14:00:00")
class PublicationStateTransitionAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_publication_admin_create_concept(self):
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        # assert that the only two legal options are concept and published
        self.assertEqual(len(form["publicatiestatus"].options), 2)
        self.assertIn(
            (
                PublicationStatusOptions.concept.value,
                False,
                PublicationStatusOptions.concept.label,
            ),
            form["publicatiestatus"].options,
        )
        self.assertIn(
            (
                PublicationStatusOptions.published.value,
                False,
                PublicationStatusOptions.published.label,
            ),
            form["publicatiestatus"].options,
        )

        form["informatie_categorieen"].force_value([ic.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
        form["publisher"] = str(organisation.pk)
        form["officiele_titel"] = "The Dali Thundering CONCEPT"

        add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        added_item = Publication.objects.get()
        self.assertEqual(added_item.publicatiestatus, PublicationStatusOptions.concept)

    @patch("woo_publications.publications.admin.index_publication.delay")
    def test_publication_admin_create_publish(
        self, mock_index_publication_delay: MagicMock
    ):
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["publisher"] = str(organisation.pk)
        form["officiele_titel"] = "Published publication"

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        added_item = Publication.objects.get()
        self.assertEqual(
            added_item.publicatiestatus, PublicationStatusOptions.published
        )
        self.assertEqual(str(added_item.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(added_item.ingetrokken_op, None)
        mock_index_publication_delay.assert_called_once_with(
            publication_id=added_item.pk
        )

    @patch("woo_publications.publications.admin.index_publication.delay")
    @patch("woo_publications.publications.admin.index_document.delay")
    def test_publication_admin_update_to_publish(
        self,
        mock_index_document_delay: MagicMock,
        mock_index_publication_delay: MagicMock,
    ):
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            publisher=organisation,
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.concept,
        )
        document = DocumentFactory.create(
            publicatie=publication,
            publicatiestatus=PublicationStatusOptions.concept,
            officiele_titel="The Dali Thundering CONCEPT",
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        # assert that the only two legal options are concept and published
        self.assertEqual(len(form["publicatiestatus"].options), 2)
        self.assertIn(
            (
                PublicationStatusOptions.concept.value,
                True,
                PublicationStatusOptions.concept.label,
            ),
            form["publicatiestatus"].options,
        )
        self.assertIn(
            (
                PublicationStatusOptions.published.value,
                False,
                PublicationStatusOptions.published.label,
            ),
            form["publicatiestatus"].options,
        )

        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        publication.refresh_from_db()
        document.refresh_from_db()
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )
        self.assertEqual(
            publication.publicatiestatus, PublicationStatusOptions.published
        )
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.published)
        self.assertEqual(str(document.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(document.ingetrokken_op, None)
        self.assertEqual(str(publication.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(publication.ingetrokken_op, None)
        mock_index_publication_delay.assert_called_once_with(
            publication_id=publication.pk
        )
        mock_index_document_delay.assert_called_once_with(
            document_id=document.pk,
            download_url=f"http://testserver{download_url}",
        )

        with self.subTest(
            "test if update log gets created for the document "
            "that states that it has been published"
        ):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                document
            ).get(extra_data__event=Events.update)
            log_extra_data = update_publication_log.extra_data

            self.assertEqual(
                log_extra_data["object_data"]["publicatiestatus"],
                PublicationStatusOptions.published,
            )

    @patch("woo_publications.publications.admin.remove_publication_from_index.delay")
    @patch("woo_publications.publications.admin.remove_document_from_index.delay")
    def test_publication_admin_update_to_revoked(
        self,
        mock_remove_document_from_index_delay: MagicMock,
        mock_remove_publication_from_index_delay: MagicMock,
    ):
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            publisher=organisation,
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.published,
        )
        document = DocumentFactory.create(
            publicatie=publication,
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="The Dali Thundering CONCEPT",
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        # assert that the only two legal options are published and revoked
        self.assertEqual(len(form["publicatiestatus"].options), 2)
        self.assertIn(
            (
                PublicationStatusOptions.published.value,
                True,
                PublicationStatusOptions.published.label,
            ),
            form["publicatiestatus"].options,
        )
        self.assertIn(
            (
                PublicationStatusOptions.revoked.value,
                False,
                PublicationStatusOptions.revoked.label,
            ),
            form["publicatiestatus"].options,
        )

        form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        publication.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(publication.publicatiestatus, PublicationStatusOptions.revoked)
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.revoked)
        self.assertEqual(str(publication.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(str(publication.ingetrokken_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(str(document.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(str(document.ingetrokken_op), "2024-09-25 14:00:00+00:00")
        mock_remove_publication_from_index_delay.assert_called_once_with(
            publication_id=publication.pk
        )
        mock_remove_document_from_index_delay.assert_called_once_with(
            document_id=document.pk,
        )

        with self.subTest(
            "test if update log gets created for the document "
            "that states that it has been revoked"
        ):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                document
            ).get(extra_data__event=Events.update)
            log_extra_data = update_publication_log.extra_data

            self.assertEqual(
                log_extra_data["object_data"]["publicatiestatus"],
                PublicationStatusOptions.revoked,
            )

    def test_document_admin_create_from_concept_publication(self):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
        )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        reverse_url = reverse("admin:publications_document_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]

        # assert that during creation publicatiestatus is readonly
        self.assertNotIn("publicatiestatus", form.fields)

        form["publicatie"] = publication.id
        form["identifier"] = identifier
        form["officiele_titel"] = "The Dali Thundering CONCEPT"
        form["creatiedatum"] = "2025-01-01"

        add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        added_item = Document.objects.get()
        self.assertEqual(added_item.gepubliceerd_op, None)
        self.assertEqual(added_item.ingetrokken_op, None)
        self.assertEqual(added_item.publicatiestatus, PublicationStatusOptions.concept)

    @patch("woo_publications.publications.admin.index_document.delay")
    def test_document_admin_create_from_publish_publication(
        self, mock_index_document_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
        )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        reverse_url = reverse("admin:publications_document_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatie"] = publication.id
        form["identifier"] = identifier
        form["officiele_titel"] = "published document"
        form["creatiedatum"] = "2025-01-01"

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        added_item = Document.objects.get()
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(added_item.uuid)}
        )
        self.assertEqual(
            added_item.publicatiestatus, PublicationStatusOptions.published
        )
        self.assertEqual(str(added_item.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(added_item.ingetrokken_op, None)
        mock_index_document_delay.assert_called_once_with(
            document_id=added_item.pk,
            download_url=f"http://testserver{download_url}",
        )

    @patch("woo_publications.publications.admin.index_document.delay")
    def test_document_admin_update_alter_published_document_reindexes_data(
        self, mock_index_document_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
        )
        document = DocumentFactory.create(
            publicatie=publication,
            publicatiestatus=PublicationStatusOptions.published,
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]

        # assert that the only two legal options are published and revoked
        self.assertEqual(len(form["publicatiestatus"].options), 2)
        self.assertIn(
            (
                PublicationStatusOptions.published.value,
                True,
                PublicationStatusOptions.published.label,
            ),
            form["publicatiestatus"].options,
        )
        self.assertIn(
            (
                PublicationStatusOptions.revoked.value,
                False,
                PublicationStatusOptions.revoked.label,
            ),
            form["publicatiestatus"].options,
        )

        form["officiele_titel"] = "published document"

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        publication.refresh_from_db()
        document.refresh_from_db()
        self.assertEqual(str(publication.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(publication.ingetrokken_op, None)
        self.assertEqual(str(document.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(document.ingetrokken_op, None)
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.published)
        mock_index_document_delay.assert_called_once_with(
            document_id=document.pk,
            download_url=f"http://testserver{download_url}",
        )

    @patch("woo_publications.publications.admin.remove_document_from_index.delay")
    def test_document_admin_update_alter_to_revoked(
        self, mock_remove_document_from_index_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        document = DocumentFactory.create(
            publicatie=publication,
            publicatiestatus=PublicationStatusOptions.published,
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertEqual(add_response.status_code, 302)
        document.refresh_from_db()
        self.assertEqual(str(document.gepubliceerd_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(str(document.ingetrokken_op), "2024-09-25 14:00:00+00:00")
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.revoked)
        mock_remove_document_from_index_delay.assert_called_once_with(
            document_id=document.pk,
        )
