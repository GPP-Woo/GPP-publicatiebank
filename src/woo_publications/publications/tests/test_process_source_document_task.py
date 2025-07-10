import base64
from datetime import date
from io import BytesIO
from uuid import uuid4

from django.core.files import File
from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import DocumentenClient, get_client
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
)
from woo_publications.utils.tests.vcr import VCRMixin

from ..tasks import process_source_document
from .factories import DocumentFactory

# this UUID is in the fixture
DOCUMENT_TYPE_UUID = "9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8"
DOCUMENT_TYPE_URL = (
    "http://host.docker.internal:8000/catalogi/api/v1/informatieobjecttypen/"
    + DOCUMENT_TYPE_UUID
)


def _create_initial_document(
    *,
    client: DocumentenClient,
    creation_date: date,
    content: bytes,
    filename: str,
    content_type: str = "text/plain",
):
    oz_document = client.create_document(
        # must be unique for the source organisation
        identification=str(uuid4()),
        source_organisation="123456782",
        document_type_url=DOCUMENT_TYPE_URL,
        creation_date=creation_date,
        title="File part test",
        filesize=len(content),  # in bytes
        filename=filename,
        content_type=content_type,
    )
    part = oz_document.file_parts[0]
    # "upload" the part
    client.proxy_file_part_upload(
        File(BytesIO(content)),
        file_part_uuid=part.uuid,
        lock=oz_document.lock,
    )
    client.unlock_document(uuid=oz_document.uuid, lock=oz_document.lock)
    return oz_document.uuid


class ProcessSourceDocumentTaskTests(VCRMixin, TestCase):
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

        cls.information_category = InformationCategoryFactory.create(
            uuid=DOCUMENT_TYPE_UUID
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_external_metadata_overwrites_local_metadata_and_content_is_copied(self):
        # create an actual document in the remote Open Zaak that we can point to
        with get_client(self.service) as client:
            oz_uuid = _create_initial_document(
                client=client,
                creation_date=date(2025, 1, 1),
                content=b"a" * 10,
                filename="data.txt",
                content_type="text/plain",
            )

        source_url = (
            "http://openzaak.docker.internal:8001/documenten/api/v1/"
            f"enkelvoudiginformatieobjecten/{oz_uuid}"
        )
        woo_document = DocumentFactory.create(
            creatiedatum=date(2000, 1, 1),
            bestandsformaat="unknown",
            bestandsnaam="unknown.bin",
            bestandsomvang=2000,
            source_url=source_url,
        )
        assert woo_document.document_service is None
        assert woo_document.document_uuid is None
        assert not woo_document.lock
        assert not woo_document.upload_complete

        process_source_document(
            document_id=woo_document.id, base_url="http://host.docker.internal:8000/"
        )

        woo_document.refresh_from_db()
        self.assertEqual(woo_document.document_service, self.service)
        self.assertIsNotNone(woo_document.document_uuid)
        self.assertEqual(woo_document.lock, "")
        self.assertTrue(woo_document.upload_complete)

        self.assertEqual(woo_document.creatiedatum, date(2025, 1, 1))
        self.assertEqual(woo_document.bestandsformaat, "text/plain")
        self.assertEqual(woo_document.bestandsnaam, "data.txt")
        self.assertEqual(woo_document.bestandsomvang, 10)

        with (
            self.subTest("verify 'copy' metadata"),
            get_client(self.service) as client,
        ):
            detail = client.get(
                f"enkelvoudiginformatieobjecten/{woo_document.document_uuid}"
            )
            assert detail.status_code == 200
            detail_data = detail.json()
            self.assertFalse(detail_data["locked"])
            self.assertEqual(detail_data["bestandsnaam"], "data.txt")
            # Postponed for later!
            # self.assertEqual(detail_data["formaat"], "text/plain")

        with (
            self.subTest("verify content is copied"),
            get_client(self.service) as client,
        ):
            download = client.get(
                f"enkelvoudiginformatieobjecten/{woo_document.document_uuid}/download"
            )

            assert download.status_code == 200
            self.assertEqual(download.content, b"aaaaaaaaaa")

    def test_copies_document_data_of_specified_version(self):
        # create a document and make multiple versions of the content
        with get_client(self.service) as client:
            oz_uuid = _create_initial_document(
                client=client,
                creation_date=date(2025, 1, 1),
                content=b"a" * 10,
                filename="data.txt",
            )
            # lock to create a new version
            lock = client.post(f"enkelvoudiginformatieobjecten/{oz_uuid}/lock").json()[
                "lock"
            ]
            client.patch(
                f"enkelvoudiginformatieobjecten/{oz_uuid}",
                json={
                    "inhoud": base64.b64encode(b"12345").decode("ascii"),
                    "bestandsnaam": "updated.txt",
                    "bestandsomvang": 5,
                    "lock": lock,
                },
            )
            client.unlock_document(uuid=oz_uuid, lock=lock)

        source_url = (
            "http://openzaak.docker.internal:8001/documenten/api/v1/"
            f"enkelvoudiginformatieobjecten/{oz_uuid}?versie=1"
        )
        woo_document = DocumentFactory.create(source_url=source_url)

        process_source_document(
            document_id=woo_document.id, base_url="http://host.docker.internal:8000/"
        )

        woo_document.refresh_from_db()
        self.assertTrue(woo_document.upload_complete)
        # values from version 1
        self.assertEqual(woo_document.creatiedatum, date(2025, 1, 1))
        self.assertEqual(woo_document.bestandsformaat, "text/plain")
        self.assertEqual(woo_document.bestandsnaam, "data.txt")
        self.assertEqual(woo_document.bestandsomvang, 10)

        with (
            self.subTest("verify content from version 1 is copied"),
            get_client(self.service) as client,
        ):
            download = client.get(
                f"enkelvoudiginformatieobjecten/{woo_document.document_uuid}/download"
            )

            assert download.status_code == 200
            self.assertEqual(download.content, b"aaaaaaaaaa")

    def test_document_creation_is_idempotent(self):
        with get_client(self.service) as client:
            oz_uuid = _create_initial_document(
                client=client,
                creation_date=date(2025, 1, 1),
                content=b"a" * 10,
                filename="data.txt",
                content_type="text/plain",
            )

        source_url = (
            "http://openzaak.docker.internal:8001/documenten/api/v1/"
            f"enkelvoudiginformatieobjecten/{oz_uuid}"
        )
        woo_document = DocumentFactory.create(source_url=source_url)

        registered_document_uuids: set[str] = set()
        for run in range(2):
            with self.subTest(processing_run=run):
                process_source_document(
                    document_id=woo_document.id,
                    base_url="http://host.docker.internal:8000/",
                )

                woo_document.refresh_from_db()
                self.assertTrue(woo_document.upload_complete)
                registered_document_uuids.add(str(woo_document.document_uuid))
                # we expect the document to be registered only once
                self.assertEqual(len(registered_document_uuids), 1)

    def test_resume_completes_upload_when_woo_document_meta_already_exists(self):
        with get_client(self.service) as client:
            oz_uuid = _create_initial_document(
                client=client,
                creation_date=date(2025, 1, 1),
                content=b"12345",
                filename="data.txt",
                content_type="text/plain",
            )

        source_url = (
            "http://openzaak.docker.internal:8001/documenten/api/v1/"
            f"enkelvoudiginformatieobjecten/{oz_uuid}"
        )
        woo_document = DocumentFactory.create(
            source_url=source_url,
            creatiedatum=date(2025, 1, 1),
            bestandsomvang=5,
            bestandsformaat="text/plain",
            bestandsnaam="data.txt",
        )
        woo_document.register_in_documents_api(
            build_absolute_uri=lambda abs_path: f"http://host.docker.internal:8000{abs_path}"
        )
        assert not woo_document.upload_complete

        process_source_document(
            document_id=woo_document.id, base_url="http://host.docker.internal:8000/"
        )

        woo_document.refresh_from_db()
        self.assertTrue(woo_document.upload_complete)
