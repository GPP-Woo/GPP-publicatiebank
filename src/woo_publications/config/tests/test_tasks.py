import uuid
from unittest.mock import MagicMock, call, patch

from django.test import TestCase

from celery.exceptions import Retry
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.contrib.catalogi_api.tests.constants import (
    DEFAULT_CATALOGUS,
    DEFAULT_IOT,
)
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    PublicationFactory,
)

from ...contrib.catalogi_api.client import CatalogiAPIError, get_client
from ...publications.constants import PublicationStatusOptions
from ...utils.tests.vcr import VCRMixin
from ..models import GlobalConfiguration
from ..tasks import (
    change_document_api_iots,
    sync_information_categories_and_documents_with_catalog_api,
)


class TestChangeDocumentAPIIOTSTask(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)

        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "documents_api_service": document_service,
                "catalogi_api_service": catalogi_service,
                "catalogus_url": "https://example.com/default",
                "default_iot_url": "https://example.com/default",
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_no_documents_api_configured(self):
        global_config = GlobalConfiguration.get_solo()
        global_config.documents_api_service = None
        global_config.save()

        with self.assertRaisesMessage(
            RuntimeError,
            "No documents API configured yet! Set up the global configuration.",
        ):
            change_document_api_iots()

    def test_no_category_api_configured(self):
        global_config = GlobalConfiguration.get_solo()
        global_config.catalogi_api_service = None
        global_config.save()

        with self.assertRaisesMessage(
            RuntimeError,
            "No catalogi API configured yet! Set up the global configuration.",
        ):
            change_document_api_iots()

    def test_no_default_iot_configured(self):
        global_config = GlobalConfiguration.get_solo()
        global_config.default_iot_url = ""
        global_config.save()

        DocumentFactory.create_batch(3)

        with self.assertRaisesMessage(
            RuntimeError,
            "The Catalogi API isn't configured fully yet, we are missing some if not "
            "all of the Catalogi API global configuration URLS.",
        ):
            change_document_api_iots()

    @patch(
        "woo_publications.publications.tasks.update_document_informatieobjecttype.delay"
    )
    def test_update_documents(
        self, mock_update_document_informatieobjecttype_delay: MagicMock
    ):
        informatie_category = InformationCategoryFactory.create(
            iot_url="https://example.com/information_category"
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[informatie_category.pk],
            publicatiestatus=PublicationStatusOptions.published,
        )
        publication_without_ic = PublicationFactory.create()
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        # cannot define revoked publication, so we have to manually save it as such.
        revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        revoked.publicatiestatus = PublicationStatusOptions.revoked
        revoked.save()
        document_1 = DocumentFactory.create(
            publicatie=publication, with_registered_document=True
        )
        document_2 = DocumentFactory.create(
            publicatie=publication_without_ic,
            with_registered_document=True,
        )
        DocumentFactory.create(
            publicatie=concept,
            with_registered_document=False,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        DocumentFactory.create(
            publicatie=revoked,
            with_registered_document=True,
            publicatiestatus=PublicationStatusOptions.revoked,
        )

        with self.captureOnCommitCallbacks(execute=True):
            change_document_api_iots()

        mock_update_document_informatieobjecttype_delay.assert_has_calls(
            [
                call(
                    document_id=document_1.pk,
                    documenttype_url="https://example.com/information_category",
                ),
                call(
                    document_id=document_2.pk,
                    documenttype_url="https://example.com/default",
                ),
            ],
            any_order=True,
        )


class TestSyncInformationCategoriesAndDocumentsWithCatalogApi(VCRMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        cls.catalogi_service = catalogi_service = ServiceFactory.create(
            for_catalogi_api_docker_compose=True
        )

        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "documents_api_service": document_service,
                "catalogi_api_service": catalogi_service,
                "catalogus_url": DEFAULT_CATALOGUS,
                "default_iot_url": DEFAULT_IOT,
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_no_documents_api_configured(self):
        global_config = GlobalConfiguration.get_solo()
        global_config.documents_api_service = None
        global_config.save()

        with self.assertRaisesMessage(
            RuntimeError,
            "No documents API configured yet! Set up the global configuration.",
        ):
            sync_information_categories_and_documents_with_catalog_api(
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
            )

    def test_no_category_api_configured(self):
        global_config = GlobalConfiguration.get_solo()
        global_config.catalogi_api_service = None
        global_config.save()

        with self.assertRaisesMessage(
            RuntimeError,
            "No catalogi API configured yet! Set up the global configuration.",
        ):
            sync_information_categories_and_documents_with_catalog_api(
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
            )

    def test_no_default_iot_configured(self):
        global_config = GlobalConfiguration.get_solo()
        global_config.default_iot_url = ""
        global_config.save()

        DocumentFactory.create_batch(3)

        with self.assertRaisesMessage(
            RuntimeError,
            "The Catalogi API isn't configured fully yet, we are missing some if not "
            "all of the Catalogi API global configuration URLS.",
        ):
            sync_information_categories_and_documents_with_catalog_api(
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
            )

    @patch("woo_publications.config.tasks.change_document_api_iots")
    def test_happy_flow(
        self,
        mock_change_document_api_iots: MagicMock,
    ):
        will_be_updated = InformationCategoryFactory.create(
            iot_url="",
            iot_uuid=None,
            naam="TestSyncInformationCategoriesAndDocumentsWithCatalogApi.test_happy_flow",
        )

        will_remain = InformationCategoryFactory.create(
            iot_url=f"{self.catalogi_service.api_root}{uuid.uuid4()}"
        )
        will_remain_iot_uuid = will_remain.iot_uuid
        will_remain_iot_url = will_remain.iot_url

        sync_information_categories_and_documents_with_catalog_api(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )

        will_be_updated.refresh_from_db()
        will_remain.refresh_from_db()

        # Since the url and uuid was empty we updated it
        self.assertNotEqual(will_be_updated.iot_url, "")
        self.assertNotEqual(will_be_updated.iot_uuid, None)
        # Since the url had the same root, it didn't change.
        self.assertEqual(will_remain.iot_url, will_remain_iot_url)
        self.assertEqual(will_remain.iot_uuid, will_remain_iot_uuid)

        with get_client(self.catalogi_service) as client:
            iot_response = client.get(will_be_updated.iot_url)
            self.assertEqual(iot_response.status_code, 200)

        mock_change_document_api_iots.assert_called_once()

    @patch("woo_publications.config.tasks.change_document_api_iots")
    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=500),
    )
    def test_client_raises_error_in_range_to_trigger_retry(
        self,
        mock_change_document_api_iots: MagicMock,
        mock_create_iot: MagicMock,
    ):
        ic = InformationCategoryFactory.create(iot_url="", iot_uuid=None)

        with self.assertRaises(Retry):
            sync_information_categories_and_documents_with_catalog_api(
                confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
            )

        ic.refresh_from_db()
        self.assertEqual(ic.iot_url, "")
        self.assertIsNone(ic.iot_uuid)
        mock_change_document_api_iots.assert_called_once()

    @patch("woo_publications.config.tasks.change_document_api_iots")
    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message", status_code=None),
    )
    def test_client_raises_other_error_will_not_trigger_retry(
        self,
        mock_change_document_api_iots: MagicMock,
        mock_create_iot: MagicMock,
    ):
        ic = InformationCategoryFactory.create(iot_url="", iot_uuid=None)

        sync_information_categories_and_documents_with_catalog_api(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )

        ic.refresh_from_db()
        self.assertEqual(ic.iot_url, "")
        self.assertIsNone(ic.iot_uuid)
        mock_change_document_api_iots.assert_called_once()
