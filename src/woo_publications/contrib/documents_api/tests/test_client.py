"""
Test the documents API client.

WOO Publications acts as a bit of a proxy - a document that gets created/registered
with us is saved into the Documents API, primarily to handle the file uploads
accordingly.

The API traffic is captured and 'mocked' using VCR.py. When re-recording the cassettes
for these tests, make sure to bring up the docker compose in the root of the repo:

.. code-block:: bash

    docker compose up

See ``docker/open-zaak/README.md`` for the test credentials and available data.

Note that we make use of the information categories fixture, which gets loaded in
the WOO Publications backend automatically. See the file
``/home/bbt/code/gpp-woo/woo-publications/src/woo_publications/fixtures/information_categories.json``
for the reference.
"""

from datetime import date
from io import BytesIO
from uuid import UUID, uuid4

from django.core.files import File
from django.test import TestCase, override_settings

from requests import RequestException

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..client import DocumentsAPIError, get_client

DOCUMENT_TYPE_URL = (
    "http://host.docker.internal:8000/catalogi/api/v1/informatieobjecttypen/"
    "9aeb7501-3f77-4f36-8c8f-d21f47c2d6e8"  # this UUID is in the fixture
)


class DocumentsAPIClientTests(VCRMixin, TestCase):
    def test_create_document_with_file_parts_upload(self):
        service = ServiceFactory.build(for_documents_api_docker_compose=True)

        with get_client(service) as client:
            document = client.create_document(
                identification=str(
                    uuid4()
                ),  # must be unique for the source organisation
                source_organisation="123456782",
                document_type_url=DOCUMENT_TYPE_URL,
                creation_date=date.today(),
                title="Sample document",
                filesize=1_000,  # in bytes
                filename="sample.png",
                content_type="image/png",
                description="a" * 5000,  # use a long string and try to break it
            )

        self.assertGreater(len(str(document.uuid)), 0)
        # we expect a lock to be returend
        self.assertIsInstance(document.lock, str)
        self.assertNotEqual(document.lock, "")

        # given the upload size & configuration of Open Zaak (100 byte chunks),
        # we expect multiple parts (see DOCUMENTEN_UPLOAD_CHUNK_SIZE envvar)
        self.assertEqual(len(parts := document.file_parts), 10)
        self.assertGreater(len(str(parts[0].uuid)), 0)
        self.assertEqual(parts[0].size, 100)

        with self.subTest("check document is created"):
            # and we expect that we can fetch the document too
            detail_response = client.get(
                f"enkelvoudiginformatieobjecten/{document.uuid}"
            )

            self.assertEqual(detail_response.status_code, 200)

    def test_proxy_file_part_upload(self):
        service = ServiceFactory.build(for_documents_api_docker_compose=True)

        uploaded_file = File(BytesIO(b"1234567890"))

        with get_client(service) as client:
            document = client.create_document(
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
            part = document.file_parts[0]

            # "upload" the part
            client.proxy_file_part_upload(
                uploaded_file,
                file_part_uuid=part.uuid,
                lock=document.lock,
            )

            # and verify that it's completed
            detail_response = client.get(
                f"enkelvoudiginformatieobjecten/{document.uuid}"
            )
            detail_response.raise_for_status()
            detail_data = detail_response.json()

        bestandsdelen = detail_data["bestandsdelen"]
        self.assertEqual(len(bestandsdelen), 1)
        self.assertTrue(bestandsdelen[0]["voltooid"])
        self.assertTrue(detail_data["locked"])

    def test_can_unlock_document_after_uploads_completed(self):
        service = ServiceFactory.build(for_documents_api_docker_compose=True)
        uploaded_file = File(BytesIO(b"123"))
        with get_client(service) as client:
            document = client.create_document(
                identification=str(
                    uuid4()
                ),  # must be unique for the source organisation
                source_organisation="123456782",
                document_type_url=DOCUMENT_TYPE_URL,
                creation_date=date.today(),
                title="File part test",
                filesize=3,  # in bytes
                filename="data.txt",
                content_type="text/plain",
            )
            part = document.file_parts[0]
            # "upload" the part
            client.proxy_file_part_upload(
                uploaded_file,
                file_part_uuid=part.uuid,
                lock=document.lock,
            )

            # and unlock the document
            client.unlock_document(uuid=document.uuid, lock=document.lock)

            # and verify that it's in the expected state
            detail_response = client.get(
                f"enkelvoudiginformatieobjecten/{document.uuid}"
            )
            detail_response.raise_for_status()
            detail_data = detail_response.json()

        self.assertFalse(detail_data["locked"])
        bestandsdelen = detail_data["bestandsdelen"]
        self.assertEqual(len(bestandsdelen), 0)

        with self.subTest("can lock document"):
            with get_client(service) as client:
                client.lock_document(uuid=document.uuid)

                # and verify that it's in the expected state
                detail_response = client.get(
                    f"enkelvoudiginformatieobjecten/{document.uuid}"
                )
                detail_response.raise_for_status()
                detail_data = detail_response.json()

            self.assertTrue(detail_data["locked"])

    @override_settings(LANGUAGE_CODE="en-en")
    def test_destroy_document_error(self):
        service = ServiceFactory.build(for_documents_api_docker_compose=True)

        with (
            get_client(service) as client,
            self.assertRaisesMessage(
                DocumentsAPIError, "Something went wrong while deleting the document."
            ),
            self.vcr_raises(RequestException),
        ):
            client.destroy_document(uuid=UUID("3fae4cd5-b122-4b34-bfd9-4617909d3f22"))

    def test_update_bronorganisatie(self):
        service = ServiceFactory.build(for_documents_api_docker_compose=True)

        with get_client(service) as client:
            # create document
            document = client.create_document(
                identification=str(
                    uuid4()
                ),  # must be unique for the source organisation
                source_organisation="123456782",
                document_type_url=DOCUMENT_TYPE_URL,
                creation_date=date.today(),
                title="Sample document",
                filesize=1_000,  # in bytes
                filename="sample.png",
            )

            # sanity check that the bronorganisatie is the given rsin
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{document.uuid}"
            )
            self.assertEqual(openzaak_response.json()["bronorganisatie"], "123456782")

            # update bronorganisatie
            client.update_document_bronorganisatie(
                uuid=document.uuid,
                source_organisation="112345670",
                lock=document.lock,
            )

            # ensure that the bronorganisatie has been updated
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{document.uuid}"
            )
            self.assertEqual(openzaak_response.json()["bronorganisatie"], "112345670")
