import re
from datetime import date
from io import BytesIO
from uuid import uuid4

from django.core.files import File
from django.test import TestCase, override_settings

import requests_mock
from celery.exceptions import Retry
from requests import Response
from requests.exceptions import HTTPError, RequestException
from rest_framework import status
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.catalogi_api.client import (
    get_client as get_catalogi_client,
)
from woo_publications.contrib.documents_api.client import (
    get_client as get_document_client,
)
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..tasks import update_document_informatieobjecttype
from .factories import DocumentFactory, PublicationFactory

response_500 = Response()
response_500.status_code = 500


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class TestUpdateDocumentIOTTask(VCRMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Set up global configuration
        cls.document_service = document_service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )
        cls.catalogi_service = catalogi_service = ServiceFactory.create(
            for_catalogi_api_docker_compose=True
        )
        config = GlobalConfiguration.get_solo()
        config.documents_api_service = document_service
        config.catalogi_api_service = catalogi_service
        config.organisation_rsin = "000000000"
        config.save()

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def setup_document(self):
        config = GlobalConfiguration.get_solo()
        uploaded_file = File(BytesIO(b"1234567890"))

        with get_document_client(self.document_service) as client:
            openzaak_document = client.create_document(
                identification=str(
                    uuid4()
                ),  # must be unique for the source organisation
                source_organisation="123456782",
                document_type_url=config.default_iot_url,
                creation_date=date.today(),
                title="File part test",
                filesize=10,  # in bytes
                filename="data.txt",
                content_type="text/plain",
            )
            part = openzaak_document.file_parts[0]

            # "upload" the part
            client.proxy_file_part_upload(
                uploaded_file,
                file_part_uuid=part.uuid,
                lock=openzaak_document.lock,
            )

            # and unlock the document
            client.unlock_document(
                uuid=openzaak_document.uuid, lock=openzaak_document.lock
            )

            # Ensure that this api call retrieves the document from openzaak
            # so we can see that it returns a 404 after deletion.
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{openzaak_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_200_OK)
            self.assertEqual(openzaak_response.json()["bronorganisatie"], "123456782")
            return openzaak_document

    def setup_catalogi(self, rsin):
        with get_catalogi_client(self.catalogi_service) as client:
            catalogus_url = client.create_catalogi(rsin=rsin)
            default_iot = client.create_iot(
                catalogus=catalogus_url,
                description="default catalogus",
                confidentiality_indication=VertrouwelijkheidsAanduidingen.vertrouwelijk,
            )

        config = GlobalConfiguration.get_solo()
        config.catalogus_url = catalogus_url
        config.default_iot_url = default_iot.url
        config.save()

    def test_no_documents_api_relation(self):
        document = DocumentFactory.create(lock="asd9asd9a9sd9asd")

        update_document_informatieobjecttype(
            document_id=document.pk, documenttype_url="http://www.example.com/"
        )

        document.refresh_from_db()
        self.assertEqual(document.lock, "asd9asd9a9sd9asd")

    def test_update_document_informatieobjecttype_happy_flow(self):
        self.setup_catalogi(rsin="314159265")
        external_document = self.setup_document()

        information_category = InformationCategoryFactory.create()
        information_category.create_iot_object(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )
        information_category.refresh_from_db()

        publication = PublicationFactory.create(
            informatie_categorieen=[information_category.pk]
        )
        document = DocumentFactory.create(
            publicatie=publication,
            document_service=self.document_service,
            document_uuid=external_document.uuid,
            lock="",
        )

        update_document_informatieobjecttype(
            document_id=document.pk, documenttype_url=information_category.iot_url
        )

        document.refresh_from_db()
        with get_document_client(self.document_service) as client:
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{external_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                openzaak_response.json()["informatieobjecttype"],
                information_category.iot_url,
            )
        self.assertEqual(document.lock, "")

    def test_error_during_locking(self):
        self.setup_catalogi(rsin="100000010")
        external_document = self.setup_document()

        information_category = InformationCategoryFactory.create()
        information_category.create_iot_object(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )
        information_category.refresh_from_db()

        publication = PublicationFactory.create(
            informatie_categorieen=[information_category.pk]
        )
        document = DocumentFactory.create(
            publicatie=publication,
            document_service=self.document_service,
            document_uuid=external_document.uuid,
            lock="",
        )

        with requests_mock.Mocker(real_http=True) as m:
            m.post(
                re.compile(
                    r"http://openzaak.docker.internal:8001/documenten/api/v1/enkelvoudiginformatieobjecten/[^/]+/lock"
                ),
                exc=RequestException,
            )
            with self.assertRaises(RequestException):
                update_document_informatieobjecttype(
                    document_id=document.pk,
                    documenttype_url=information_category.iot_url,
                )

        document.refresh_from_db()
        self.assertEqual(document.lock, "")

    def test_error_during_locking_with_retry(self):
        self.setup_catalogi(rsin="100000022")
        external_document = self.setup_document()

        information_category = InformationCategoryFactory.create()
        information_category.create_iot_object(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )
        information_category.refresh_from_db()

        publication = PublicationFactory.create(
            informatie_categorieen=[information_category.pk]
        )
        document = DocumentFactory.create(
            publicatie=publication,
            document_service=self.document_service,
            document_uuid=external_document.uuid,
            lock="",
        )

        with requests_mock.Mocker(real_http=True) as m:
            m.post(
                re.compile(
                    r"http://openzaak.docker.internal:8001/documenten/api/v1/enkelvoudiginformatieobjecten/[^/]+/lock"
                ),
                exc=HTTPError("500 Internal Server Error", response=response_500),
            )
            with self.assertRaises(Retry):
                update_document_informatieobjecttype(
                    document_id=document.pk,
                    documenttype_url=information_category.iot_url,
                )

        document.refresh_from_db()
        self.assertEqual(document.lock, "")

    def test_error_during_update_document_iot(self):
        self.setup_catalogi(rsin="100000034")
        external_document = self.setup_document()

        information_category = InformationCategoryFactory.create()
        information_category.create_iot_object(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )
        information_category.refresh_from_db()

        publication = PublicationFactory.create(
            informatie_categorieen=[information_category.pk]
        )
        document = DocumentFactory.create(
            publicatie=publication,
            document_service=self.document_service,
            document_uuid=external_document.uuid,
            lock="",
        )

        with requests_mock.Mocker(real_http=True) as m:
            m.post(
                re.compile(
                    r"http://openzaak.docker.internal:8001/documenten/api/v1/enkelvoudiginformatieobjecten/[^/]+"
                ),
                exc=RequestException,
            )
            with self.assertRaises(RequestException):
                update_document_informatieobjecttype(
                    document_id=document.pk,
                    documenttype_url=information_category.iot_url,
                )

        document.refresh_from_db()
        self.assertEqual(document.lock, "")

    def test_error_during_update_document_iot_with_retry(self):
        self.setup_catalogi(rsin="100000046")
        external_document = self.setup_document()

        information_category = InformationCategoryFactory.create()
        information_category.create_iot_object(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )
        information_category.refresh_from_db()

        publication = PublicationFactory.create(
            informatie_categorieen=[information_category.pk]
        )
        document = DocumentFactory.create(
            publicatie=publication,
            document_service=self.document_service,
            document_uuid=external_document.uuid,
            lock="",
        )

        with requests_mock.Mocker(real_http=True) as m:
            m.post(
                re.compile(
                    r"http://openzaak.docker.internal:8001/documenten/api/v1/enkelvoudiginformatieobjecten/[^/]+"
                ),
                exc=HTTPError("500 Internal Server Error", response=response_500),
            )
            with self.assertRaises(Retry):
                update_document_informatieobjecttype(
                    document_id=document.pk,
                    documenttype_url=information_category.iot_url,
                )

        document.refresh_from_db()
        self.assertEqual(document.lock, "")
