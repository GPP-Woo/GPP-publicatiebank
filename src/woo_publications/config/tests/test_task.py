import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase

from celery.exceptions import Retry

from woo_publications.config.models import GlobalConfiguration
from woo_publications.config.tasks import index_default_iot
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError
from woo_publications.contrib.catalogi_api.typing import IOT
from woo_publications.contrib.tests.factories import ServiceFactory


class IndexDefaultIOTTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "catalogi_api_service": service,
                "catalogus_url": "https://example.com/catalogi",
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_no_catalogi_url_set(self):
        global_config = GlobalConfiguration.objects.get()
        global_config.catalogus_url = ""
        global_config.save()

        with self.assertRaisesMessage(
            RuntimeError, "No catalog configured yet! Set up the global configuration."
        ):
            index_default_iot()

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        return_value=IOT(
            uuid=uuid.uuid4(),
            url="https://example.com/iot",
        ),
    )
    def test_no_catalogi_api_service_set(self, mock_create_iot: MagicMock):
        index_default_iot()

        global_config = GlobalConfiguration.objects.get()
        self.assertTrue(global_config.default_iot_url, mock_create_iot.return_value.url)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=None),
    )
    def test_client_raises_error_with_no_status_code(self, mock_create_iot: MagicMock):
        with self.assertRaisesMessage(
            CatalogiAPIError,
            "some message",
        ):
            index_default_iot()

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=404),
    )
    def test_client_raises_error_with_none_retry_status_code(
        self, mock_create_iot: MagicMock
    ):
        with self.assertRaisesMessage(
            CatalogiAPIError,
            "some message",
        ):
            index_default_iot()

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=500),
    )
    def test_client_raises_error_in_range_to_trigger_retry(
        self, mock_create_iot: MagicMock
    ):
        with self.assertRaises(Retry):
            index_default_iot.run()
