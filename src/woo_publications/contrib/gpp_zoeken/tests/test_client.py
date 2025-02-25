from django.test import TestCase

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    PublicationFactory,
)
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

    def test_remove_unpublished_document_from_index(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)

        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            doc = DocumentFactory.build(
                publicatiestatus=publication_status,
                uuid="5e033c6c-6430-46c1-9efd-05899ec63382",
            )

            with self.subTest(publication_status), get_client(service) as client:
                task_id = client.remove_document_from_index(doc)

                self.assertIsNotNone(task_id)
                self.assertIsInstance(task_id, str)
                self.assertNotEqual(task_id, "")

    def test_remove_published_document_from_index(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)

        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        with (
            get_client(service) as client,
            self.assertRaises(ValueError),
        ):
            client.remove_document_from_index(doc)

    def test_index_unpublished_publication(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)
        client = get_client(service)

        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            publication = PublicationFactory.create(publicatiestatus=publication_status)
            with (
                self.subTest(publication_status=publication_status),
                client,
                self.assertRaises(ValueError),
            ):
                client.index_publication(publication)

    def test_index_published_publication(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        with get_client(service) as client:
            task_id = client.index_publication(publication)

        self.assertIsNotNone(task_id)
        self.assertIsInstance(task_id, str)
        self.assertNotEqual(task_id, "")
