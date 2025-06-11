from django.test import TestCase

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    PublicationFactory,
    TopicFactory,
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

            if publication_status == PublicationStatusOptions.revoked:
                doc = DocumentFactory.create(
                    publicatie__revoked=True,
                    publicatiestatus=publication_status,
                )
            else:
                doc = DocumentFactory.create(
                    publicatie__publicatiestatus=publication_status,
                    publicatiestatus=publication_status,
                )

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

            publication = PublicationFactory.build(publicatiestatus=publication_status)
            doc = DocumentFactory.build(
                publicatie=publication,
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

            if publication_status == PublicationStatusOptions.revoked:
                publication = PublicationFactory.create(revoked=True)
            else:
                publication = PublicationFactory.create(
                    publicatiestatus=publication_status
                )

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

    def test_remove_unpublished_publication_from_index(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)

        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            doc = PublicationFactory.build(
                publicatiestatus=publication_status,
                uuid="5e033c6c-6430-46c1-9efd-05899ec63382",
            )

            with self.subTest(publication_status), get_client(service) as client:
                task_id = client.remove_publication_from_index(doc)

                self.assertIsNotNone(task_id)
                self.assertIsInstance(task_id, str)
                self.assertNotEqual(task_id, "")

    def test_remove_published_publication_from_index(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)

        doc = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        with (
            get_client(service) as client,
            self.assertRaises(ValueError),
        ):
            client.remove_publication_from_index(doc)

    def test_index_unpublished_topic(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)
        client = get_client(service)

        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            topic = TopicFactory.create(publicatiestatus=publication_status)
            with (
                self.subTest(publication_status=publication_status),
                client,
                self.assertRaises(ValueError),
            ):
                client.index_topic(topic)

    def test_index_published_topic(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)
        topic = TopicFactory.create(publicatiestatus=PublicationStatusOptions.published)

        with get_client(service) as client:
            task_id = client.index_topic(topic)

        self.assertIsNotNone(task_id)
        self.assertIsInstance(task_id, str)
        self.assertNotEqual(task_id, "")

    def test_remove_unpublished_topic_from_index(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)

        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            topic = TopicFactory.build(
                publicatiestatus=publication_status,
                uuid="632d1653-023b-4ada-9eb0-6d1c6f279274",
            )

            with self.subTest(publication_status), get_client(service) as client:
                task_id = client.remove_topic_from_index(topic)

                self.assertIsNotNone(task_id)
                self.assertIsInstance(task_id, str)
                self.assertNotEqual(task_id, "")

    def test_remove_published_topic_from_index(self):
        service = ServiceFactory.build(for_gpp_search_docker_compose=True)

        topic = TopicFactory.create(publicatiestatus=PublicationStatusOptions.published)

        with (
            get_client(service) as client,
            self.assertRaises(ValueError),
        ):
            client.remove_topic_from_index(topic)
