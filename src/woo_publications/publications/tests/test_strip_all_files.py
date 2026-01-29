import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.file_processing import strip_all_files
from woo_publications.publications.tests.factories import DocumentFactory
from woo_publications.utils.tests.vcr import VCRMixin


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
@patch("woo_publications.publications.tasks.strip_pdf.delay")
class TestUpdateThemeFromWaardenlijstCommand(VCRMixin, TestCase):
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

    def test_no_configuration(self, mock_strip_pdf: MagicMock):
        config = GlobalConfiguration.get_solo()
        config.gpp_search_service = None
        config.save()

        with self.assertRaisesMessage(
            AssertionError, "Search API services not configured."
        ):
            strip_all_files(base_url="http://host.docker.internal:8000/")

        mock_strip_pdf.assert_not_called()

    def test_no_documents(self, mock_strip_pdf: MagicMock):
        count = strip_all_files(base_url="http://host.docker.internal:8000/")

        self.assertEqual(count, 0)
        mock_strip_pdf.assert_not_called()

    def test_happy_flow_documents(self, mock_strip_pdf: MagicMock):
        document = DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=True,
            bestandsformaat="application/pdf",
        )
        count = strip_all_files(base_url="http://host.docker.internal:8000/")

        self.assertEqual(count, 1)
        mock_strip_pdf.assert_called_once_with(
            document_id=document.pk,
            base_url="http://host.docker.internal:8000/",
        )

    def test_documents_not_eligible_for_stripping(self, mock_strip_pdf: MagicMock):
        DocumentFactory.create(
            upload_complete=True,
            bestandsformaat="application/pdf",
        )
        DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=False,
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
        mock_strip_pdf.assert_not_called()
