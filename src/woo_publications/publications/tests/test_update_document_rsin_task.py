from datetime import date
from io import BytesIO
from uuid import uuid4

from django.core.files import File
from django.test import TestCase, override_settings

import requests_mock
from requests import HTTPError
from rest_framework import status

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import get_client
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..tasks import update_document_rsin
from .factories import DocumentFactory


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class TestUpdateDocumentRsinTask(VCRMixin, TestCase):
    DOCUMENT_TYPE_UUID = "9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8"

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

    def setup_document(self):
        uploaded_file = File(BytesIO(b"1234567890"))
        DOCUMENT_TYPE_URL = (
            "http://host.docker.internal:8000/catalogi/api/v1/informatieobjecttypen/"
            "9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8"  # this UUID is in the fixture
        )

        with get_client(self.service) as client:
            openzaak_document = client.create_document(
                identification=str(
                    uuid4()
                ),  # must be unique for the source organisation
                source_organisation="123456782",
                document_type_url=DOCUMENT_TYPE_URL,
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

    def test_update_document_happy_flow(self):
        external_document = self.setup_document()
        document = DocumentFactory.create(
            document_service=self.service, document_uuid=external_document.uuid, lock=""
        )

        update_document_rsin(document_id=document.pk, rsin="112345670")

        document.refresh_from_db()
        with get_client(self.service) as client:
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{external_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_200_OK)
            self.assertEqual(openzaak_response.json()["bronorganisatie"], "112345670")
        self.assertEqual(document.lock, "")

    def test_update_document_with_existing_lock(self):
        external_document = self.setup_document()
        with get_client(self.service) as client:
            lock = client.lock_document(uuid=external_document.uuid)

        document = DocumentFactory.create(
            document_service=self.service,
            document_uuid=external_document.uuid,
            lock=lock,
        )

        update_document_rsin(document_id=document.pk, rsin="112345670")

        document.refresh_from_db()
        with get_client(self.service) as client:
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{external_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_200_OK)
            self.assertEqual(openzaak_response.json()["bronorganisatie"], "112345670")
        self.assertEqual(document.lock, "")

    def test_update_document_with_error_still_unlocks_itself(self):
        external_document = self.setup_document()
        document = DocumentFactory.create(
            document_service=self.service, document_uuid=external_document.uuid, lock=""
        )

        with requests_mock.Mocker(real_http=True) as m:
            m.register_uri(
                requests_mock.PATCH,
                f"http://openzaak.docker.internal:8001/documenten/api/v1/enkelvoudiginformatieobjecten/{external_document.uuid}",
                status_code=400,
            )
            with self.assertRaises(HTTPError):
                update_document_rsin(document_id=document.pk, rsin="112345670")

        document.refresh_from_db()
        with get_client(self.service) as client:
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{external_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_200_OK)
            self.assertEqual(openzaak_response.json()["bronorganisatie"], "123456782")
        self.assertEqual(document.lock, "")

    def test_update_document_without_external_document_connected(self):
        document = DocumentFactory.create(lock="should-remain")

        update_document_rsin(document_id=document.pk, rsin="112345670")

        document.refresh_from_db()
        # if the document doesn't have a 'document_uuid' or 'document_service'
        # attached it should skip over every part which alters the internal and
        # external document, so the lock should remain.
        self.assertEqual(document.lock, "should-remain")
        # check if vcr has made any outwards requests which should be 0 because
        # all the document api stuff is getting skipped over.
        # https://vcrpy.readthedocs.io/en/latest/advanced.html
        if self.vcr_enabled:
            self.assertEqual(len(self.cassette), 0)
