from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import PublicationStatusOptions
from ..tasks import remove_document_from_index
from .factories import DocumentFactory


class RemoveDocumentFromIndexTaskTests(VCRMixin, TestCase):

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
        doc = DocumentFactory.create(publicatiestatus=PublicationStatusOptions.revoked)

        remote_task_id = remove_document_from_index(document_id=doc.pk)

        self.assertIsNone(remote_task_id)

    def test_index_skipped_for_published_document(self):
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        remote_task_id = remove_document_from_index(document_id=doc.pk)

        self.assertIsNone(remote_task_id)

    def test_remove_revoked_document(self):
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked,
            upload_complete=True,
        )

        remote_task_id = remove_document_from_index(document_id=doc.pk)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")
