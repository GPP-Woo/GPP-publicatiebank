import uuid
from io import StringIO
from unittest.mock import MagicMock, call, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from .factories import DocumentFactory


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
@patch("woo_publications.publications.tasks.strip_metadata.si")
@patch("woo_publications.publications.tasks.index_document.si")
class StripAllFilesTest(VCRMixin, TestCase):
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
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://host.docker.internal:8000/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(out.getvalue(), "Search API services not configured.\n")
        mock_strip_metadata.assert_not_called()
        mock_index_document.assert_not_called()

    def test_no_documents(
        self, mock_index_document: MagicMock, mock_strip_metadata: MagicMock
    ):
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://host.docker.internal:8000/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(
            out.getvalue(), "0 documents scheduled to strip their metadata.\n"
        )
        mock_strip_document.assert_not_called()
        mock_index_document.assert_not_called()

    def test_strip_pdf(
        self, mock_index_document: MagicMock, mock_strip_document: MagicMock
    ):
        document = DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=True,
            bestandsformaat="application/pdf",
        )
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://host.docker.internal:8000/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(
            out.getvalue(), "1 documents scheduled to strip their metadata.\n"
        )
        mock_strip_document.assert_called_once_with(
            document_id=document.pk,
            base_url="http://host.docker.internal:8000/",
        )
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )
        mock_index_document.assert_called_once_with(
            document_id=document.pk,
            download_url=f"http://host.docker.internal:8000{download_url}",
        )

    def test_strip_open_document(
        self, mock_index_document: MagicMock, mock_strip_document: MagicMock
    ):
        document = DocumentFactory.create(
            document_service=self.service,
            document_uuid=str(uuid.uuid4()),
            upload_complete=True,
            bestandsformaat="application/vnd.oasis.opendocument.text",
        )
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://host.docker.internal:8000/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(
            out.getvalue(), "2 documents scheduled to strip their metadata.\n"
        )

        mock_strip_metadata.assert_has_calls(
            [
                call(
                    document_id=pdf.pk,
                    base_url="http://host.docker.internal:8000/",
                ),
                call(
                    document_id=open_document.pk,
                    base_url="http://host.docker.internal:8000/",
                ),
            ],
            any_order=True,
        )

        pdf_download_url = reverse(
            "api:document-download", kwargs={"uuid": str(pdf.uuid)}
        )
        open_document_download_url = reverse(
            "api:document-download", kwargs={"uuid": str(open_document.uuid)}
        )

        mock_index_document.assert_has_calls(
            [
                call(
                    document_id=pdf.pk,
                    download_url=f"http://host.docker.internal:8000{pdf_download_url}",
                ),
                call(
                    document_id=open_document.pk,
                    download_url=f"http://host.docker.internal:8000{open_document_download_url}",
                ),
            ],
            any_order=True,
        )


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
@patch("woo_publications.publications.tasks.strip_metadata.si")
@patch("woo_publications.publications.tasks.index_document.si")
class StripAllFileNoVCRTest(TestCase):
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

    def test_incorrect_url(
        self, mock_index_document: MagicMock, mock_strip_metadata: MagicMock
    ):
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="https://bad-host-and-port:9999/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(
            out.getvalue(), "The provided base_url does not lead to this website.\n"
        )
        mock_strip_metadata.assert_not_called()
        mock_index_document.assert_not_called()
