from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import PublicationStatusOptions
from ..tasks import remove_from_index_by_uuid, remove_publication_from_index
from .factories import PublicationFactory


class RemovePublicationFromIndexTaskTests(VCRMixin, TestCase):
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
        publication = PublicationFactory.create(revoked=True)

        remote_task_id = remove_publication_from_index(publication_id=publication.pk)

        self.assertIsNone(remote_task_id)

    def test_remove_from_index_skipped_for_published_publication(self):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        remote_task_id = remove_publication_from_index(publication_id=publication.pk)

        self.assertIsNone(remote_task_id)

    def test_remove_revoked_publication(self):
        publication = PublicationFactory.create(
            uuid="1e4ed09f-c4d1-4eae-acf3-6b1378d8c05b",
            revoked=True,
        )

        remote_task_id = remove_publication_from_index(publication_id=publication.pk)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")

    def test_remove_published_publication_forced(self):
        publication = PublicationFactory.create(
            uuid="1e4ed09f-c4d1-4eae-acf3-6b1378d8c05b",
            publicatiestatus=PublicationStatusOptions.published,
        )

        remote_task_id = remove_publication_from_index(
            publication_id=publication.pk, force=True
        )

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")

    def test_remove_by_uuid(self):
        remote_task_id = remove_from_index_by_uuid(
            model_name="Publication",
            uuid="86b4df60-36d6-478e-8866-1293a5eac725",
        )

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")

    def test_remove_by_uuid_skipped_if_no_client_configured(self):
        config = GlobalConfiguration.get_solo()
        config.gpp_search_service = None
        config.save()

        remote_task_id = remove_from_index_by_uuid(
            model_name="Publication",
            uuid="86b4df60-36d6-478e-8866-1293a5eac725",
        )

        self.assertIsNone(remote_task_id)
