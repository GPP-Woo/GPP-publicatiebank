from django.test import TestCase

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.tests.factories import DocumentFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..client import get_client


class SearchClientTests(VCRMixin, TestCase):
    def test_index_unpublished_document(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)
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

    def test_index_published_document(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        with get_client(service) as client:
            task_id = client.index_document(doc)

        self.assertIsNotNone(task_id)
        self.assertIsInstance(task_id, str)
        self.assertNotEqual(task_id, "")
