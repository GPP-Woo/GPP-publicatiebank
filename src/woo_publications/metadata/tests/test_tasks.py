import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase

from celery.exceptions import Retry
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError
from woo_publications.contrib.catalogi_api.typing import IOT
from woo_publications.contrib.tests.factories import ServiceFactory

from ..tasks import index_iot, update_iot_description
from .factories import InformationCategoryFactory


class IndexIOTTest(TestCase):
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

    def test_no_global_config_catalogi_service_set(self):
        global_config = GlobalConfiguration.objects.get()
        global_config.catalogi_api_service = None
        global_config.save()
        information_category = InformationCategoryFactory.create()

        with self.assertRaisesMessage(
            RuntimeError,
            "No catalogi API configured yet! Set up the global configuration.",
        ):
            index_iot(
                information_category_id=information_category.pk,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
            )

    def test_no_global_config_catalogus_url_set(self):
        global_config = GlobalConfiguration.objects.get()
        global_config.catalogus_url = ""
        global_config.save()
        information_category = InformationCategoryFactory.create()

        with self.assertRaisesMessage(
            RuntimeError,
            "No catalogi API configured yet! Set up the global configuration.",
        ):
            index_iot(
                information_category_id=information_category.pk,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
            )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        return_value=IOT(
            uuid=uuid.uuid4(),
            url="https://example.com/iot",
        ),
    )
    def test_no_catalogi_object_set(self, mock_create_iot: MagicMock):
        information_category = InformationCategoryFactory.create()

        index_iot(
            information_category_id=information_category.pk,
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
        )

        information_category.refresh_from_db()

        self.assertTrue(
            information_category.iot_uuid, mock_create_iot.return_value.uuid
        )
        self.assertTrue(information_category.iot_url, mock_create_iot.return_value.url)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=None),
    )
    def test_client_raises_error_with_no_status_code(self, mock_create_iot: MagicMock):
        information_category = InformationCategoryFactory.create()

        with self.assertRaisesMessage(
            CatalogiAPIError,
            "some message",
        ):
            index_iot(
                information_category_id=information_category.pk,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
            )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=404),
    )
    def test_client_raises_error_with_none_retry_status_code(
        self, mock_create_iot: MagicMock
    ):
        information_category = InformationCategoryFactory.create()

        with self.assertRaisesMessage(
            CatalogiAPIError,
            "some message",
        ):
            index_iot(
                information_category_id=information_category.pk,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
            )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=500),
    )
    def test_client_raises_error_in_range_to_trigger_retry(
        self, mock_create_iot: MagicMock
    ):
        information_category = InformationCategoryFactory.create()

        with self.assertRaises(Retry):
            index_iot.run(
                information_category_id=information_category.pk,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
            )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        return_value=IOT(uuid=uuid.uuid4(), url="https://example.com/iot/new"),
    )
    def test_index_iot_is_idempotent(self, mock_create_iot: MagicMock):
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


class UpdateIOTDescription(TestCase):
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

    def test_no_global_config_catalogi_service_set(self):
        global_config = GlobalConfiguration.objects.get()
        global_config.catalogi_api_service = None
        global_config.save()
        information_category = InformationCategoryFactory.create()

        with self.assertRaisesMessage(
            RuntimeError,
            "No catalogi API configured yet! Set up the global configuration.",
        ):
            update_iot_description(information_category_id=information_category.pk)

    def test_no_global_config_catalogi_urls_set(self):
        global_config = GlobalConfiguration.objects.get()
        global_config.catalogus_url = ""
        global_config.default_iot_url = ""
        global_config.save()
        information_category = InformationCategoryFactory.create()

        with self.assertRaisesMessage(
            RuntimeError,
            "No catalogi API configured yet! Set up the global configuration.",
        ):
            update_iot_description(information_category_id=information_category.pk)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.update_iot_description"
    )
    def test_information_category_has_no_iot_configured(
        self, mock_update_iot_description: MagicMock
    ):
        information_category = InformationCategoryFactory.create()

        update_iot_description(information_category_id=information_category.pk)

        mock_update_iot_description.assert_not_called()

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.update_iot_description"
    )
    def test_happy_flow(self, mock_update_iot_description: MagicMock):
        iot_uuid = uuid.uuid4()
        information_category = InformationCategoryFactory.create(
            iot_uuid=iot_uuid,
            iot_url="https://example.com/iot/" + str(iot_uuid),
            naam="a brand new description!",
        )

        update_iot_description(information_category_id=information_category.pk)

        mock_update_iot_description.assert_called_once_with(
            uuid=iot_uuid,
            description="a brand new description!",
        )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.update_iot_description",
        side_effect=CatalogiAPIError(message="some message", status_code=404),
    )
    def test_client_raises_error_with_none_retry_status_code(
        self, mock_update_iot_description: MagicMock
    ):
        iot_uuid = uuid.uuid4()
        information_category = InformationCategoryFactory.create(
            iot_uuid=iot_uuid,
            iot_url="https://example.com/iot/" + str(iot_uuid),
            naam="a brand new description!",
        )

        with self.assertRaisesMessage(
            CatalogiAPIError,
            "some message",
        ):
            update_iot_description(information_category_id=information_category.pk)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.update_iot_description",
        side_effect=CatalogiAPIError(message="some message", status_code=500),
    )
    def test_client_raises_error_in_range_to_trigger_retry(
        self, mock_update_iot_description: MagicMock
    ):
        iot_uuid = uuid.uuid4()
        information_category = InformationCategoryFactory.create(
            iot_uuid=iot_uuid,
            iot_url="https://example.com/iot/" + str(iot_uuid),
            naam="a brand new description!",
        )

        with self.assertRaises(Retry):
            update_iot_description(information_category_id=information_category.pk)
