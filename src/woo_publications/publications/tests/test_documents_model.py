import uuid
from unittest.mock import MagicMock, patch

from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase, override_settings

from django_fsm import TransitionNotAllowed
from rest_framework import status
from zgw_consumers.constants import APITypes

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)
from woo_publications.utils.tests.vcr import VCRMixin

from ...contrib.documents_api.client import get_client
from ..constants import PublicationStatusOptions
from ..models import Document
from .factories import DocumentFactory


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class TestDocumentApi(VCRMixin, TestCase):
    DOCUMENT_TYPE_UUID = "9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8"
    DOCUMENT_TYPE_URL = (
        "http://host.docker.internal:8000/catalogi/api/v1/informatieobjecttypen/"
        + DOCUMENT_TYPE_UUID
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Set up global configuration
        cls.service = service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )
        config = GlobalConfiguration.get_solo()
        config.documents_api_service = service
        config.organisation_rsin = "000000000"
        config.save()

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_document_api_constraint(self):
        service = ServiceFactory.create(
            api_root="https://example.com/",
            api_type=APITypes.drc,
        )

        with self.subTest(
            "provided both service and uuid configured creates item with no errors"
        ):
            document = DocumentFactory.create(
                document_service=service, document_uuid=uuid.uuid4()
            )
            self.assertIsNotNone(document.pk)

        with self.subTest(
            "provided no service and uuid configured creates item with no errors"
        ):
            document = DocumentFactory.create(document_service=None, document_uuid=None)
            self.assertIsNotNone(document.pk)

        with (
            self.subTest(
                "provided only service and no uuid configured results in error"
            ),
            self.assertRaises(IntegrityError),
            transaction.atomic(),
        ):
            DocumentFactory.create(document_service=service, document_uuid=None)

        with (
            self.subTest(
                "provided only uuid and no service configured results in error"
            ),
            self.assertRaises(IntegrityError),
            transaction.atomic(),
        ):
            DocumentFactory.create(document_service=None, document_uuid=uuid.uuid4())

    def test_register_document_expectedly_crashes_wihout_configuration(self):
        self.addCleanup(GlobalConfiguration.clear_cache)
        config = GlobalConfiguration.get_solo()
        config.documents_api_service = None
        config.organisation_rsin = ""
        config.save()
        document: Document = DocumentFactory.create()

        with self.assertRaises(RuntimeError):
            document.register_in_documents_api(lambda s: s)

    def test_status_change_with_none_existing_publication(self):
        # TODO: when the field is protected, direct assignment will not be possible
        # TODO: if we enable factory/model level consistency checks, this will not be
        # possible either
        request = RequestFactory().post("/irrelevant")
        with (
            self.subTest("publish concept document without related publication"),
            self.assertRaises(TransitionNotAllowed),
        ):
            concept_document = Document(
                publicatie=None,
                publicatiestatus=PublicationStatusOptions.concept,
            )

            concept_document.publish(request)

        with (
            self.subTest("revoke published document without related publication"),
            self.assertRaises(TransitionNotAllowed),
        ):
            published_document = Document(
                publicatie=None,
                publicatiestatus=PublicationStatusOptions.published,
            )

            published_document.revoke()

    @patch("woo_publications.publications.api.viewsets.index_document.delay")
    def test_given_rsin_from_global_config(self, mock_index_document: MagicMock):
        information_category = InformationCategoryFactory.create(
            uuid=self.DOCUMENT_TYPE_UUID
        )
        publisher = OrganisationFactory.create(is_actief=True, rsin="")
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[information_category],
            publicatie__publisher=publisher,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )

        with get_client(document.document_service) as client:
            detail = client.get(
                f"enkelvoudiginformatieobjecten/{document.document_uuid}"
            )
            self.assertEqual(detail.status_code, status.HTTP_200_OK)
            detail_data = detail.json()
            self.assertEqual(detail_data["bronorganisatie"], "000000000")

    @patch("woo_publications.publications.api.viewsets.index_document.delay")
    def test_given_rsin_from_publisher(self, mock_index_document: MagicMock):
        information_category = InformationCategoryFactory.create(
            uuid=self.DOCUMENT_TYPE_UUID
        )
        publisher = OrganisationFactory.create(is_actief=True, rsin="123456782")
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[information_category],
            publicatie__publisher=publisher,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )

        with get_client(document.document_service) as client:
            detail = client.get(
                f"enkelvoudiginformatieobjecten/{document.document_uuid}"
            )
            self.assertEqual(detail.status_code, status.HTTP_200_OK)
            detail_data = detail.json()
            self.assertEqual(detail_data["bronorganisatie"], "123456782")
