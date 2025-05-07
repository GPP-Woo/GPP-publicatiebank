from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import PublicationStatusOptions
from ..tasks import remove_from_index_by_uuid, remove_topic_from_index
from .factories import TopicFactory


class RemoveTopicFromIndexTaskTests(VCRMixin, TestCase):
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
        topic = TopicFactory.create(publicatiestatus=PublicationStatusOptions.revoked)

        remote_task_id = remove_topic_from_index(topic_id=topic.pk)

        self.assertIsNone(remote_task_id)

    def test_index_skipped_for_published_topic(self):
        topic = TopicFactory.create(publicatiestatus=PublicationStatusOptions.published)

        remote_task_id = remove_topic_from_index(topic_id=topic.pk)

        self.assertIsNone(remote_task_id)

    def test_remove_revoked_topic(self):
        topic = TopicFactory.create(
            uuid="f2e399fe-2c2f-4c12-a9cf-0c22778e171c",
            publicatiestatus=PublicationStatusOptions.revoked,
        )

        remote_task_id = remove_topic_from_index(topic_id=topic.pk)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")

    def test_remove_published_topic_forced(self):
        topic = TopicFactory.create(
            uuid="1233f505-97f9-47f3-b767-e2215bffe0bf",
            publicatiestatus=PublicationStatusOptions.published,
        )

        remote_task_id = remove_topic_from_index(topic_id=topic.pk, force=True)

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")

    def test_remove_by_uuid(self):
        remote_task_id = remove_from_index_by_uuid(
            model_name="Topic",
            uuid="de7c7543-e2fb-43e8-953a-9e1c9a4150e4",
        )

        self.assertIsNotNone(remote_task_id)
        self.assertIsInstance(remote_task_id, str)
        self.assertNotEqual(remote_task_id, "")

    def test_remove_by_uuid_skipped_if_no_client_configured(self):
        config = GlobalConfiguration.get_solo()
        config.gpp_search_service = None
        config.save()

        remote_task_id = remove_from_index_by_uuid(
            model_name="Topic",
            uuid="76df1e22-f3d2-4708-b8bb-bfee71c83387",
        )

        self.assertIsNone(remote_task_id)
