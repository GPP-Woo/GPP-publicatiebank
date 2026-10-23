import uuid
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..models import GlobalConfiguration

CATALOGI_API_ROOT = "http://openzaak.docker.internal:8001/catalogi/api/v1/"


@patch(
    "woo_publications.config.tasks.sync_information_categories_and_documents_with_catalog_api.delay"
)
class SetupCatalogiAPICommandTests(VCRMixin, TestCase):
    """
    Open Zaak allows only one catalogus per RSIN (and domain), so every test that
    creates one uses its own RSIN.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.documents_service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "documents_api_service": cls.documents_service,
                "organisation_rsin": "123456782",
            },
        )

    def setUp(self):
        super().setUp()
        # setUpTestData cached the instance, including the related services
        GlobalConfiguration.clear_cache()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @staticmethod
    def _update_config(**fields):
        # save through the instance, solo caches it
        config = GlobalConfiguration.get_solo()
        for name, value in fields.items():
            setattr(config, name, value)
        config.save()

    def _call_command(self) -> str:
        stdout = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("setup_catalogi_api", stdout=stdout)
        return stdout.getvalue()

    def test_happy_flow(self, mock_sync_delay: MagicMock):
        self._update_config(organisation_rsin="500000001")
        information_category = InformationCategoryFactory.create(
            iot_url="https://example.com/iot", iot_uuid=uuid.uuid4()
        )

        output = self._call_command()

        self.assertIn("Catalogi API has been set up successfully.", output)
        config = GlobalConfiguration.get_solo()
        service = config.catalogi_api_service
        assert service is not None
        self.assertNotEqual(service.pk, self.documents_service.pk)
        self.assertEqual(service.label, "Open Zaak Catalogi API")
        self.assertEqual(service.slug, "open-zaak-catalogi-api")
        self.assertEqual(service.api_type, APITypes.ztc)
        self.assertEqual(service.api_root, CATALOGI_API_ROOT)
        with get_client(service) as client:
            catalogus_response = client.get(config.catalogus_url)
            self.assertEqual(catalogus_response.status_code, 200)
            self.assertEqual(catalogus_response.json()["rsin"], "500000001")

            iot_response = client.get(config.default_iot_url)
            self.assertEqual(iot_response.status_code, 200)
        information_category.refresh_from_db()
        self.assertEqual(information_category.iot_url, "")
        self.assertIsNone(information_category.iot_uuid)
        mock_sync_delay.assert_called_once_with(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )

    def test_uses_configured_catalogi_service(self, mock_sync_delay: MagicMock):
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        self._update_config(
            organisation_rsin="500000013", catalogi_api_service=catalogi_service
        )

        self._call_command()

        config = GlobalConfiguration.get_solo()
        self.assertEqual(config.catalogi_api_service, catalogi_service)
        self.assertEqual(Service.objects.filter(api_type=APITypes.ztc).count(), 1)
        self.assertTrue(config.catalogus_url.startswith(CATALOGI_API_ROOT))
        self.assertTrue(config.default_iot_url.startswith(CATALOGI_API_ROOT))
        mock_sync_delay.assert_called_once()

    def test_already_set_up(self, mock_sync_delay: MagicMock):
        self._update_config(
            catalogus_url="https://example.com/catalogus",
            default_iot_url="https://example.com/iot",
        )

        with self.assertRaisesMessage(
            CommandError, "The Catalogi API is already set up."
        ):
            self._call_command()

        self.assertFalse(Service.objects.filter(api_type=APITypes.ztc).exists())
        mock_sync_delay.assert_not_called()

    def test_no_documents_service(self, mock_sync_delay: MagicMock):
        self._update_config(documents_api_service=None)

        with self.assertRaisesMessage(
            CommandError, "No Documents API service is configured."
        ):
            self._call_command()

        self.assertFalse(Service.objects.filter(api_type=APITypes.ztc).exists())

    def test_documents_service_not_open_zaak(self, mock_sync_delay: MagicMock):
        Service.objects.filter(pk=self.documents_service.pk).update(
            api_root="https://documents.example.com/api/v1/"
        )

        with self.assertRaisesMessage(CommandError, "it doesn't look like Open Zaak"):
            self._call_command()

        self.assertFalse(Service.objects.filter(api_type=APITypes.ztc).exists())
        config = GlobalConfiguration.get_solo()
        self.assertIsNone(config.catalogi_api_service)

    def test_catalogi_service_slug_taken(self, mock_sync_delay: MagicMock):
        ServiceFactory.create(slug="open-zaak-catalogi-api")

        with self.assertRaisesMessage(
            CommandError, "Could not create the Catalogi API service"
        ):
            self._call_command()

        config = GlobalConfiguration.get_solo()
        self.assertIsNone(config.catalogi_api_service)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message"),
    )
    def test_creating_iot_fails(
        self, mock_create_iot: MagicMock, mock_sync_delay: MagicMock
    ):
        self._update_config(organisation_rsin="500000025")

        with self.assertRaisesMessage(
            CommandError,
            "Something went wrong while trying to create the default "
            "Informationobjecttypes.",
        ):
            self._call_command()

        # the created service and catalogus are kept, so the command can be rerun
        config = GlobalConfiguration.get_solo()
        assert config.catalogi_api_service is not None
        self.assertEqual(config.catalogi_api_service.api_root, CATALOGI_API_ROOT)
        self.assertTrue(config.catalogus_url.startswith(CATALOGI_API_ROOT))
        self.assertEqual(config.default_iot_url, "")
        mock_sync_delay.assert_not_called()
