import uuid
from unittest.mock import MagicMock, call, patch

from django.test import TestCase, override_settings
from django.urls import reverse

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.file_processing import strip_all_files
from woo_publications.publications.tests.factories import DocumentFactory


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
@patch("woo_publications.publications.tasks.strip_metadata.si")
@patch("woo_publications.publications.tasks.index_document.si")
class TestUpdateThemeFromWaardenlijstCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        cls.service = document_service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )

        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "gpp_search_service": search_service,
                "documents_api_service": document_service,
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_no_configuration(
        self, mock_index_document: MagicMock, mock_strip_metadata: MagicMock
    ):
        config = GlobalConfiguration.get_solo()
        config.gpp_search_service = None
        config.save()

        with self.assertRaisesMessage(
            AssertionError, "Search API services not configured."
        ):
            strip_all_files(base_url="http://host.docker.internal:8000/")

        mock_strip_metadata.assert_not_called()
        mock_index_document.assert_not_called()

    def test_no_documents(
        self, mock_index_document: MagicMock, mock_strip_metadata: MagicMock
    ):
        count = strip_all_files(base_url="http://host.docker.internal:8000/")

        self.assertEqual(count, 0)
        mock_strip_metadata.assert_not_called()
        mock_index_document.assert_not_called()

    def test_happy_flow_documents(
        self, mock_index_document: MagicMock, mock_strip_metadata: MagicMock
    ):
        upload_complete = DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=True,
            bestandsformaat="application/pdf",
        )
        upload_incomplete = DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=False,
            bestandsformaat="application/pdf",
        )
        count = strip_all_files(base_url="http://host.docker.internal:8000/")

        self.assertEqual(count, 2)
        mock_strip_metadata.assert_has_calls(
            [
                call(
                    document_id=upload_complete.pk,
                    base_url="http://host.docker.internal:8000/",
                ),
                call(
                    document_id=upload_incomplete.pk,
                    base_url="http://host.docker.internal:8000/",
                ),
            ],
            any_order=True,
        )
        complete_download_url = reverse(
            "api:document-download", kwargs={"uuid": str(upload_complete.uuid)}
        )
        incomplete_download_url = reverse(
            "api:document-download", kwargs={"uuid": str(upload_incomplete.uuid)}
        )

        mock_index_document.assert_has_calls(
            [
                call(
                    document_id=upload_complete.pk,
                    download_url=f"http://host.docker.internal:8000{complete_download_url}",
                ),
                call(
                    document_id=upload_incomplete.pk,
                    download_url=f"http://host.docker.internal:8000{incomplete_download_url}",
                ),
            ],
            any_order=True,
        )

    def test_documents_not_eligible_for_stripping(
        self, mock_index_document: MagicMock, mock_strip_metadata: MagicMock
    ):
        DocumentFactory.create(
            upload_complete=True,
            bestandsformaat="application/pdf",
        )
        DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=True,
            bestandsformaat="application/txt",
        )
        DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.concept,
            publicatiestatus=PublicationStatusOptions.concept,
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=True,
            bestandsformaat="application/txt",
        )

        count = strip_all_files(base_url="http://host.docker.internal:8000/")

        self.assertEqual(count, 0)
        mock_strip_metadata.assert_not_called()
        mock_index_document.assert_not_called()
