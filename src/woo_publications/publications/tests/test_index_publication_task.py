from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import PublicationStatusOptions
from ..tasks import index_publication
from .factories import PublicationFactory


class IndexPublicationTaskTests(VCRMixin, TestCase):
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
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        remote_task_id = index_publication(publication_id=publication.pk)

        self.assertIsNone(remote_task_id)

    def test_index_skipped_for_unpublished_publication(self):
        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            if publication_status == PublicationStatusOptions.revoked:
                publication = PublicationFactory.create(revoked=True)
            else:
                publication = PublicationFactory.create(
                    publicatiestatus=publication_status
                )

            with self.subTest(publication_status=publication_status):
                remote_task_id = index_publication(publication_id=publication.pk)

                self.assertIsNone(remote_task_id)

    def test_index_published_publication(self):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        remote_task_id = index_publication(publication_id=publication.pk)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")
