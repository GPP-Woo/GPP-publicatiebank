from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import PublicationStatusOptions
from ..tasks import index_document
from .factories import DocumentFactory


class IndexDocumentTaskTests(VCRMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={"gpp_search_service": service},
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_index_skipped_if_no_client_configured(self):
        config = GlobalConfiguration.get_solo()
        config.gpp_search_service = None
        config.save()
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        remote_task_id = index_document(document_id=doc.pk)

        self.assertIsNone(remote_task_id)

    def test_index_skipped_for_unpublished_document(self):
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

            with self.subTest(publication_status=publication_status):
                remote_task_id = index_document(document_id=doc.pk)

                self.assertIsNone(remote_task_id)

    def test_index_skipped_for_incomplete_uploads(self):
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            upload_complete=False,
        )

        remote_task_id = index_document(document_id=doc.pk)

        self.assertIsNone(remote_task_id)

    def test_index_published_document(self):
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            upload_complete=True,
        )

        remote_task_id = index_document(document_id=doc.pk)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")
