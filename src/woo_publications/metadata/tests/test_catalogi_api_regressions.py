import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.catalogi_api.typing import IOT
from woo_publications.contrib.tests.factories import ServiceFactory

from ..tasks import index_iot
from .factories import InformationCategoryFactory


class IndexIOTRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "catalogi_api_service": ServiceFactory.create(
                    for_catalogi_api_docker_compose=True
                ),
                "catalogus_url": "https://example.com/catalogus",
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        return_value=IOT(uuid=uuid.uuid4(), url="https://example.com/iot/new"),
    )
    def test_index_iot_is_idempotent(self, mock_create_iot: MagicMock):
        """
        This test should probably move to metadata/test_task..

        the task is scheduled for every IC with an empty ``iot_url`` on
        every container start (and on admin saves). When a task runs for an IC that
        got its IOT in the meantime, a duplicate (published) IOT is created.
        """
        existing_iot_uuid = uuid.uuid4()
        information_category = InformationCategoryFactory.create(
            iot_url="https://example.com/iot/existing", iot_uuid=existing_iot_uuid
        )

        index_iot(
            information_category_id=information_category.pk,
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
        )

        mock_create_iot.assert_not_called()
        information_category.refresh_from_db()
        self.assertEqual(
            information_category.iot_url, "https://example.com/iot/existing"
        )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        return_value=IOT(uuid=uuid.uuid4(), url="https://example.com/iot/new"),
    )
    def test_create_iot_object_requires_catalogus(self, mock_create_iot: MagicMock):
        """
        when catalogus creation failed (silently), the IOT is created with
        ``catalogus=""``, which the Catalogi API rejects with a non-retried 400.
        """
        config = GlobalConfiguration.get_solo()
        config.catalogus_url = ""
        config.save()
        information_category = InformationCategoryFactory.create()

        with self.assertRaises(
            RuntimeError, msg="IOT creation is attempted with an empty catalogus."
        ):
            information_category.create_iot_object(
                VertrouwelijkheidsAanduidingen.openbaar
            )

        mock_create_iot.assert_not_called()
