from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import PublicationStatusOptions
from ..tasks import index_topic
from .factories import TopicFactory


class IndexTopicTaskTests(VCRMixin, TestCase):
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
        topic = TopicFactory.create(publicatiestatus=PublicationStatusOptions.published)

        remote_task_id = index_topic(topic_id=topic.pk)

        self.assertIsNone(remote_task_id)

    def test_index_skipped_for_unpublished_topic(self):
        for publication_status in PublicationStatusOptions:
            if publication_status == PublicationStatusOptions.published:
                continue

            topic = TopicFactory.create(publicatiestatus=publication_status)
            with self.subTest(publication_status=publication_status):
                remote_task_id = index_topic(topic_id=topic.pk)

                self.assertIsNone(remote_task_id)

    def test_index_published_topic(self):
        topic = TopicFactory.create(publicatiestatus=PublicationStatusOptions.published)

        remote_task_id = index_topic(topic_id=topic.pk)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")
