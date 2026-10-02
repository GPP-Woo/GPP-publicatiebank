from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.api.tests.mixins import TokenAuthMixin
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory

from ..replace_document_iot_objects import change_document_api_iots
from ..tasks import update_document_informatieobjecttype
from .factories import DocumentFactory, PublicationFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class DocumentCreateWithoutCatalogiConfigTests(TokenAuthMixin, APITestCase):
    """
    Rigth after upgrading, ``default_iot_url`` is empty until an admin configures
    the Catalogi API. ``Document.get_iot_url`` raises a ``RuntimeError`` which isn't
    handled by the API -> HTTP 500.

    I need to sleep on this.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = GlobalConfiguration.get_solo()
        config.documents_api_service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )
        config.organisation_rsin = "000000000"
        # state right after upgrading: no catalogi API configured
        config.catalogi_api_service = None
        config.catalogus_url = ""
        config.default_iot_url = ""
        config.save()

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)
        # return the 500 response instead of re-raising the exception in the test
        self.client.raise_request_exception = False

    def test_create_document_without_default_iot_does_not_crash(self):
        information_category = InformationCategoryFactory.create(
            iot_url="https://example.com/iot"
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[information_category]
        )
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "officieleTitel": "Testdocument",
            "creatiedatum": "2024-11-05",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 10,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("api:document-list"), data=body, headers=AUDIT_HEADERS
            )

        self.assertNotEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Missing Catalogi configuration results in an unhandled server error.",
        )


class DocumentGetIOTURLTests(TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_information_category_iot_used_without_default_iot(self):
        """
        related to test_create_document_without_default_iot_does_not_crash

        the default IOT is only needed for documents without an
        information category, yet it is checked first and blocks every document.
        """
        config = GlobalConfiguration.get_solo()
        config.default_iot_url = ""
        config.save()
        information_category = InformationCategoryFactory.create(
            iot_url="https://example.com/iot"
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[information_category]
        )
        document = DocumentFactory.create(publicatie=publication)

        try:
            iot_url = document.get_iot_url
        except RuntimeError as exc:
            self.fail(f"Missing default IOT blocks a document with an IC IOT: {exc}")

        self.assertEqual(iot_url, "https://example.com/iot")


class UpdateDocumentIOTUploadLockTests(TestCase):
    @patch(
        "woo_publications.contrib.documents_api.client.DocumentenClient.unlock_document"
    )
    @patch(
        "woo_publications.contrib.documents_api.client.DocumentenClient.update_document_iot"
    )
    @patch(
        "woo_publications.contrib.documents_api.client.DocumentenClient.lock_document"
    )
    def test_does_not_release_lock_of_upload_in_progress(
        self,
        mock_lock_document: MagicMock,
        mock_update_document_iot: MagicMock,
        mock_unlock_document: MagicMock,
    ):
        """
        ``document.lock`` holds the lock of an in-progress (multi-part)
        upload. The task reuses it and unlocks the document afterwards, so the
        remaining file parts of the upload can no longer be uploaded.

        Locks are way too easy to make mistakes with... I posted in #team-bron
        than requiring ETag in `If-Match` request header is way safer. (and more
        performant)
        """
        document = DocumentFactory.create(
            with_registered_document=True,
            lock="upload-in-progress-lock",
            upload_complete=False,
        )

        update_document_informatieobjecttype(
            document_id=document.pk, documenttype_url="https://example.com/iot"
        )

        document.refresh_from_db()
        self.assertEqual(document.lock, "upload-in-progress-lock")
        mock_unlock_document.assert_not_called()


class ChangeDocumentAPIIOTsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "documents_api_service": ServiceFactory.create(
                    for_documents_api_docker_compose=True
                ),
                "catalogi_api_service": ServiceFactory.create(
                    for_catalogi_api_docker_compose=True
                ),
                "default_iot_url": "https://example.com/default",
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @patch(
        "woo_publications.publications.tasks.update_document_informatieobjecttype.delay"
    )
    def test_one_bad_document_does_not_abort_the_others(
        self, mock_update_delay: MagicMock
    ):
        """
        a single information category without ``iot_url`` raises inside
        the loop and aborts it halfway, after tasks were already scheduled for
        earlier documents.
        """
        ic_without_iot = InformationCategoryFactory.create(iot_url="")
        ic_with_iot = InformationCategoryFactory.create(
            iot_url="https://example.com/ok"
        )
        DocumentFactory.create(
            publicatie=PublicationFactory.create(
                informatie_categorieen=[ic_without_iot]
            ),
        )
        good_document = DocumentFactory.create(
            publicatie=PublicationFactory.create(informatie_categorieen=[ic_with_iot]),
        )

        try:
            change_document_api_iots()
        except RuntimeError as exc:
            self.fail(f"One misconfigured document aborts the whole run: {exc}")

        mock_update_delay.assert_any_call(
            document_id=good_document.pk, documenttype_url="https://example.com/ok"
        )
