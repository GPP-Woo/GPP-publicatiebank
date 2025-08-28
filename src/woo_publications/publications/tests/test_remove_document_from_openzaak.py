from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from django.core.files import File
from django.test import TestCase, override_settings

from rest_framework import status

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import DocumentsAPIError, get_client
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy
from woo_publications.publications.tasks import remove_document_from_documents_api
from woo_publications.publications.tests.factories import DocumentFactory
from woo_publications.utils.tests.vcr import VCRMixin


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class TestRemoveDocumentFromOpenZaakTask(VCRMixin, TestCase):
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

        cls.document = DocumentFactory.create()
        cls.user = UserFactory.create()

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_delete_task_happy_flow(self):
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

        with self.captureOnCommitCallbacks(execute=True):
            remove_document_from_documents_api(
                document_id=self.document.pk,
                user_id=self.user.pk,
                service_uuid=self.service.uuid,
                document_uuid=openzaak_document.uuid,
            )

        with get_client(self.service) as client:
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{openzaak_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            TimelineLogProxy.objects.for_object(self.document)  # pyright: ignore[reportAttributeAccessIssue]
            .filter(extra_data__event=Events.delete_document)
            .exists()
        )

    def test_document_not_in_openzaak_create_no_errors(self):
        remove_document_from_documents_api(
            document_id=self.document.pk,
            user_id=self.user.pk,
            service_uuid=self.service.uuid,
            document_uuid=UUID("f83a9443-b667-4b5d-8131-7953cc7b9bc1"),
        )

    def test_no_error_raised_when_OZ_returns_404(self):
        remove_document_from_documents_api(
            document_id=self.document.pk,
            user_id=self.user.pk,
            service_uuid=self.service.uuid,
            document_uuid=UUID("f83a9443-b667-4b5d-8131-7953cc7b9bc1"),
        )

        self.assertFalse(
            TimelineLogProxy.objects.for_object(self.document)  # pyright: ignore[reportAttributeAccessIssue]
            .filter(extra_data__event=Events.delete_document)
            .exists()
        )

    @patch(
        "woo_publications.contrib.documents_api.client.DocumentenClient.destroy_document",
        side_effect=DocumentsAPIError(message="error"),
    )
    def test_create_log_when_openzaak_has_error(self, mock_destroy_document: MagicMock):
        remove_document_from_documents_api(
            document_id=self.document.pk,
            user_id=self.user.pk,
            service_uuid=self.service.uuid,
            document_uuid=UUID("f83a9443-b667-4b5d-8131-7953cc7b9bc1"),
        )

        log = TimelineLogProxy.objects.for_object(self.document).get(  # pyright: ignore[reportAttributeAccessIssue]
            extra_data__event=Events.delete_document
        )
        expected_data = {
            "event": Events.delete_document,
            "acting_user": {
                "identifier": self.user.pk,
                "display_name": self.user.get_full_name(),
            },
            "document_data": {
                "success": False,
                "service_uuid": str(self.service.uuid),
                "document_uuid": "f83a9443-b667-4b5d-8131-7953cc7b9bc1",
            },
            "_cached_object_repr": "",
        }
        self.assertEqual(log.extra_data, expected_data)
