import io
import zipfile
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings
from django.core.files import File
from django.test import TestCase
from django.test.utils import override_settings

import magic
from pypdf import PdfReader
from rest_framework import status

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ...contrib.documents_api.client import get_client
from ...metadata.tests.factories import InformationCategoryFactory
from ..constants import PublicationStatusOptions
from ..file_processing import MIN_META
from ..tasks import strip_document
from .factories import DocumentFactory

METADATA_PDF = (
    Path(settings.DJANGO_PROJECT_DIR) / "publications" / "tests" / "files" / "amore.pdf"
)


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class StripMetaDataTaskTestCase(VCRMixin, TestCase):
    # this UUID is in the fixture
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
        config.organisation_rsin = "123456782"
        config.save()

        # create Information Category to ensure the document_type_url
        # matches DOCUMENT_TYPE_URL
        InformationCategoryFactory.create(
            uuid=cls.DOCUMENT_TYPE_UUID,
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def _get_vcr_kwargs(self, **kwargs):
        kwargs.setdefault("ignore_hosts", ("invalid-domain",))
        return super()._get_vcr_kwargs(**kwargs)

    def _create_document_in_documents_api(self, file, name, size) -> UUID:
        document_mime = magic.from_buffer(file.read(2048), mime=True)
        bestandsformaat = document_mime

        file.seek(0)

        with get_client(self.service) as client:
            openzaak_document = client.create_document(
                identification=str(
                    uuid4()
                ),  # must be unique for the source organisation
                source_organisation="123456782",
                document_type_url=self.DOCUMENT_TYPE_URL,
                creation_date=date.today(),
                title="strip metadata test",
                filesize=size,  # in bytes
                filename=name,
                content_type=bestandsformaat,
            )

            for part in openzaak_document.file_parts:
                file_part = File(io.BytesIO(file.read(part.size)))

                client.proxy_file_part_upload(
                    file=file_part,
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

        return openzaak_document.uuid

    def test_skip_stripping_if_no_client_configured(self):
        config = GlobalConfiguration.get_solo()
        config.gpp_search_service = None
        config.save()
        doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )

        with self.assertRaisesMessage(
            AssertionError, "The document must have a Documents API object attached"
        ):
            strip_document(document_id=doc.pk, base_url="http://testserver/")

        self.assertEqual(doc.metadata_gestript_op, None)

    def test_strip_pdf_of_metadata(self):
        with METADATA_PDF.open("rb") as pdf_file:
            reader = PdfReader(pdf_file)
            meta = reader.metadata
            assert meta
            self.assertEqual(
                meta,
                {
                    "/Author": "Dean Martin",
                    "/Creator": "pypdf",
                    "/Title": "That's Amore",
                    "/Subject": "Pizza Pie",
                    "/Keywords": "Moray Eel",
                },
            )

            xmp_metadata = reader.xmp_metadata
            assert xmp_metadata
            self.assertEqual(xmp_metadata.dc_creator, ["Dean Martin"])
            self.assertEqual(xmp_metadata.pdf_keywords, "Moray Eel")
            self.assertEqual(xmp_metadata.pdf_producer, "pypdf")

            file_size = Path(pdf_file.name).stat().st_size

            document_reference = self._create_document_in_documents_api(
                file=pdf_file, name=pdf_file.name, size=file_size
            )

        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            bestandsnaam=pdf_file.name,
            bestandsomvang=file_size,
            bestandsformaat="application/pdf",
            document_service=self.service,
            document_uuid=document_reference,
        )

        strip_document(
            document_id=document.pk,
            base_url="http://host.docker.internal:8000",
        )

        document.refresh_from_db()
        self.assertIsNotNone(document.metadata_gestript_op)

        with get_client(self.service) as client:
            documents_api_document = client.get(
                f"enkelvoudiginformatieobjecten/{document.document_uuid}/download"
            )
            document_content = documents_api_document.content

        reader = PdfReader(io.BytesIO(document_content))
        assert reader.metadata
        # Ensure that the correct fields are stripped.
        self.assertEqual(
            reader.metadata,
            {
                "/Author": "",
                "/Creator": "pypdf",
                "/Title": "",
                "/Subject": "",
                "/Keywords": "",
            },
        )
        xmp_metadata = reader.xmp_metadata
        assert xmp_metadata
        self.assertListEqual(xmp_metadata.dc_creator, [])  # pyright: ignore [reportArgumentType]
        self.assertIsNone(xmp_metadata.pdf_keywords)
        self.assertEqual(xmp_metadata.pdf_producer, "pypdf")

    def test_strip_open_documents_of_metadata(self):
        OPEN_DOCUMENT_FOLDER = (
            Path(settings.DJANGO_PROJECT_DIR)
            / "publications"
            / "tests"
            / "files"
            / "open_documents"
        )

        for file_type in ["odt", "ods", "odp", "odg"]:
            with self.subTest(file_type):
                open_document_path = OPEN_DOCUMENT_FOLDER / f"hello_world.{file_type}"

                with zipfile.ZipFile(open_document_path) as open_document_zip:
                    meta_file_data = open_document_zip.read("meta.xml")

                    assert meta_file_data
                    self.assertNotEqual(meta_file_data, MIN_META)

                file_size = open_document_path.stat().st_size

                with open(open_document_path, "rb") as file:
                    document_reference = self._create_document_in_documents_api(
                        file=file, name=f"hello_world.{file_type}", size=file_size
                    )

                    document = DocumentFactory.create(
                        publicatiestatus=PublicationStatusOptions.published,
                        bestandsnaam=f"hello_world.{file_type}",
                        bestandsomvang=file_size,
                        document_service=self.service,
                        document_uuid=document_reference,
                    )

                strip_document(
                    document_id=document.pk,
                    base_url="http://host.docker.internal:8000",
                )

                document.refresh_from_db()
                self.assertIsNotNone(document.metadata_gestript_op)

                with get_client(self.service) as client:
                    documents_api_document = client.get(
                        f"enkelvoudiginformatieobjecten/{document.document_uuid}/download"
                    )
                    document_content = documents_api_document.content

                with zipfile.ZipFile(io.BytesIO(document_content)) as open_document_zip:
                    for info in open_document_zip.infolist():
                        if info.filename == "meta.xml":
                            meta_file_data = open_document_zip.read(info.filename)

                    self.assertEqual(meta_file_data, MIN_META)
