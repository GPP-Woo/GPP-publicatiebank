from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.tests.factories import DocumentFactory

from ..client import get_client


class SearchClientTests(TestCase):
    def setUp(self):
        super().setUp()

        GlobalConfiguration.clear_cache
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_index_unpublished_document(self):
        service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        client = get_client(service)

        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            doc = DocumentFactory.create(publicatiestatus=publication_status)
            with (
                self.subTest(publication_status=publication_status),
                client,
                self.assertRaises(ValueError),
            ):
                client.index_document(doc)
