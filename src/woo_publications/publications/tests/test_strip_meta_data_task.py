import io
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings
from django.core.files import File
from django.test import TestCase
from django.test.utils import override_settings

from pypdf import PdfReader
from rest_framework import status

from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ...contrib.documents_api.client import get_client
from ...metadata.tests.factories import InformationCategoryFactory
from ..constants import PublicationStatusOptions
from ..tasks import strip_pdf
from .factories import DocumentFactory

METADATA_PDF = (
    Path(settings.DJANGO_PROJECT_DIR) / "publications" / "tests" / "files" / "amore.pdf"
)
METADATA_PDF_SIZE = 12_622


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

    def _create_document_in_documents_api(self) -> UUID:
        # create temporary named file to create a pdf which we can strip
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

            pdf_file.seek(0)

            with get_client(self.service) as client:
                openzaak_document = client.create_document(
                    identification=str(
                        uuid4()
                    ),  # must be unique for the source organisation
                    source_organisation="123456782",
                    document_type_url=self.DOCUMENT_TYPE_URL,
                    creation_date=date.today(),
                    title="File part test",
                    filesize=METADATA_PDF_SIZE,  # in bytes
                    filename="foobar.pdf",
                    content_type="application/pdf",
                )

                for part in openzaak_document.file_parts:
                    file = File(io.BytesIO(pdf_file.read(part.size)))

                    client.proxy_file_part_upload(
                        file=file, file_part_uuid=part.uuid, lock=openzaak_document.lock
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
            strip_pdf(document_id=doc.pk, base_url="http://testserver/")

    def test_strip_pdf_of_metadata(self):
        document_reference = self._create_document_in_documents_api()
        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            bestandsnaam="foobar.pdf",
            bestandsomvang=METADATA_PDF_SIZE,
            bestandsformaat="application/pdf",
            document_service=self.service,
            document_uuid=document_reference,
        )

        completed = strip_pdf(
            document_id=document.pk,
            base_url="http://host.docker.internal:8000",
        )
        self.assertTrue(completed)

        document.refresh_from_db()

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
