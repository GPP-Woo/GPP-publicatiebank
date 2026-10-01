from unittest.mock import MagicMock, call, patch

from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.publications.replace_document_iot_objects import (
    change_document_api_iots,
)
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    PublicationFactory,
)


class TestChangeDocumentAPIIOTS(TestCase):
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
            "No default Information Objecttype url configured yet! "
            "Set up the global configuration.",
        ):
            change_document_api_iots()

    def test_informatie_categories_has_no_iot_urls(self):
        informatie_category = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[informatie_category.pk],
        )
        DocumentFactory.create_batch(3, publicatie=publication)

        with self.assertRaisesMessage(
            RuntimeError,
            "The catalogi API data has not been loaded from the "
            "'load_information_categories' management command, "
            "please load the information categories before continuing.",
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
        )
        publication_without_ic = PublicationFactory.create()
        document_1 = DocumentFactory.create(
            publicatie=publication,
        )
        document_2 = DocumentFactory.create(
            publicatie=publication_without_ic,
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
