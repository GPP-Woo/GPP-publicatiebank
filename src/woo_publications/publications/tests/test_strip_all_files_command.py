import uuid
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings

import requests_mock

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
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
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://host.docker.internal:8000/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(out.getvalue(), "Search API services not configured.\n")
        mock_strip_pdf.assert_not_called()

    @requests_mock.Mocker()
    def test_incorrect_url(self, mock_strip_pdf: MagicMock, m):
        m.register_uri(requests_mock.GET, requests_mock.ANY, status_code=404)

        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://incorrect.url/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(
            out.getvalue(), "The provided base_url does not lead to this website.\n"
        )
        mock_strip_pdf.assert_not_called()

    def test_no_documents(self, mock_strip_pdf: MagicMock):
        out = StringIO()

        call_command(
            "strip_all_files",
            base_url="http://host.docker.internal:8000/",
            verbosity=0,
            stdout=out,
            no_color=True,
        )

        self.assertEqual(
            out.getvalue(), "0 documents scheduled to strip its metadata.\n"
        )
        mock_strip_pdf.assert_not_called()

    def test_happy_flow_documents(self, mock_strip_pdf: MagicMock):
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
            out.getvalue(), "1 documents scheduled to strip its metadata.\n"
        )
        mock_strip_pdf.assert_called_once_with(
            document_id=document.pk,
            base_url="http://host.docker.internal:8000/",
        )
