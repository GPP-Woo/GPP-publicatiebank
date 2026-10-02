from unittest.mock import MagicMock, call, patch

from django.core.management import call_command
from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    PublicationFactory,
)


class TestChangeDocumentAPIIOTCommand(TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @patch(
        "woo_publications.publications.tasks.update_document_informatieobjecttype.delay"
    )
    def test_happy_flow(
        self, mock_update_document_informatieobjecttype_delay: MagicMock
    ):
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

        call_command("set_real_document_iots")

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
