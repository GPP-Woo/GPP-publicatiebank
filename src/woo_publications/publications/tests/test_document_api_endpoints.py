from collections.abc import Iterator
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import StreamingHttpResponse
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from freezegun import freeze_time
from requests.exceptions import ConnectionError, HTTPError
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import APIKeyUnAuthorizedMixin, TokenAuthMixin
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import get_client
from woo_publications.contrib.documents_api.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import DocumentActionTypeOptions, PublicationStatusOptions
from ..models import Document
from .factories import DocumentFactory, PublicationFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class DocumentApiAuthorizationAndPermissionTests(APIKeyUnAuthorizedMixin, APITestCase):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:document-list")
        detail_endpoint = reverse("api:document-detail", kwargs={"uuid": str(uuid4())})

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_result_in_301_with_wrong_credentials(self):
        document = DocumentFactory.create()
        list_url = reverse("api:document-list")
        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)


class DocumentApiReadTests(TokenAuthMixin, APITestCase):
    def test_list_documents(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(verantwoordelijke=organisation)
        publication2 = PublicationFactory.create(verantwoordelijke=None)
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.concept,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            document2 = DocumentFactory.create(
                publicatie=publication2,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                creatiedatum="2024-02-02",
            )

        response = self.client.get(reverse("api:document-list"), headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

        with self.subTest("first_item_in_response_with_expected_data"):
            documenthandelingen = [
                {
                    "soortHandeling": DocumentActionTypeOptions.declared,
                    "atTime": "2024-09-24T14:00:00+02:00",
                    "wasAssciatedWith": None,
                }
            ]
            expected_second_item_data = {
                "uuid": str(document2.uuid),
                "identifier": "document-2",
                "publicatie": str(publication2.uuid),
                "officieleTitel": "title two",
                "verkorteTitel": "two",
                "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                "publicatiestatus": PublicationStatusOptions.published,
                "creatiedatum": "2024-02-02",
                "bestandsformaat": "unknown",
                "bestandsnaam": "unknown.bin",
                "bestandsomvang": 0,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "bestandsdelen": None,
                "documenthandelingen": documenthandelingen,
            }

            self.assertEqual(data["results"][0], expected_second_item_data)

        with self.subTest("second_item_in_response_with_expected_data"):
            documenthandelingen = [
                {
                    "soortHandeling": DocumentActionTypeOptions.declared,
                    "atTime": "2024-09-25T14:30:00+02:00",
                    "wasAssciatedWith": str(organisation.uuid),
                }
            ]
            expected_first_item_data = {
                "uuid": str(document.uuid),
                "identifier": "document-1",
                "publicatie": str(publication.uuid),
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.concept,
                "creatiedatum": "2024-01-01",
                "bestandsformaat": "unknown",
                "bestandsnaam": "unknown.bin",
                "bestandsomvang": 0,
                "registratiedatum": "2024-09-25T14:30:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
                "bestandsdelen": None,
                "documenthandelingen": documenthandelingen,
            }

            self.assertEqual(data["results"][1], expected_first_item_data)

    def test_list_documents_filter_order(self):
        publication, publication2 = PublicationFactory.create_batch(2)
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            document2 = DocumentFactory.create(
                publicatie=publication2,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                creatiedatum="2024-02-02",
            )

        # registratiedatum
        with self.subTest("creatiedatum_ascending"):
            response = self.client.get(
                reverse("api:document-list"),
                {"sorteer": "creatiedatum"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0]["uuid"], str(document.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(document2.uuid))

        with self.subTest("creatiedatum_descending"):
            response = self.client.get(
                reverse("api:document-list"),
                {"sorteer": "-creatiedatum"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0]["uuid"], str(document2.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(document.uuid))

        # Officiele titel
        with self.subTest("officiele_title_ascending"):
            response = self.client.get(
                reverse("api:document-list"),
                {"sorteer": "officiele_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0]["uuid"], str(document.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(document2.uuid))

        with self.subTest("officiele_title_descending"):
            response = self.client.get(
                reverse("api:document-list"),
                {"sorteer": "-officiele_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0]["uuid"], str(document2.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(document.uuid))

        # short titel
        with self.subTest("verkorte_titel_ascending"):
            response = self.client.get(
                reverse("api:document-list"),
                {"sorteer": "verkorte_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0]["uuid"], str(document.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(document2.uuid))

        with self.subTest("verkorte_titel_descending"):
            response = self.client.get(
                reverse("api:document-list"),
                {"sorteer": "-verkorte_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0]["uuid"], str(document2.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(document.uuid))

    def test_list_document_publication_filter(self):
        publication, publication2 = PublicationFactory.create_batch(2)
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.concept,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            DocumentFactory.create(
                publicatie=publication2,
                publicatiestatus=PublicationStatusOptions.concept,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                creatiedatum="2024-02-02",
            )

        response = self.client.get(
            reverse("api:document-list"),
            {"publicatie": str(publication.uuid)},
            headers=AUDIT_HEADERS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["uuid"], str(document.uuid))

    def test_list_document_identifier_filter(self):
        publication, publication2 = PublicationFactory.create_batch(2)
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            DocumentFactory.create(
                publicatie=publication2,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                creatiedatum="2024-02-02",
            )

        response = self.client.get(
            reverse("api:document-list"),
            {"identifier": "document-1"},
            headers=AUDIT_HEADERS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["uuid"], str(document.uuid))

    def test_list_document_filter_publication_status(self):
        published = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        concept = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        revoked = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked
        )
        list_url = reverse("api:document-list")

        with self.subTest("filter on published publications"):
            response = self.client.get(
                list_url,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(published.uuid))

        with self.subTest("filter on concept publications"):
            response = self.client.get(
                list_url,
                {"publicatiestatus": PublicationStatusOptions.concept},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(concept.uuid))

        with self.subTest("filter on revoked publications"):
            response = self.client.get(
                list_url,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(revoked.uuid))

    def test_detail_document(self):
        publication = PublicationFactory.create()
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        documenthandelingen = [
            {
                "soortHandeling": DocumentActionTypeOptions.declared,
                "atTime": "2024-09-25T14:30:00+02:00",
                "wasAssciatedWith": None,
            }
        ]
        expected_data = {
            "uuid": str(document.uuid),
            "identifier": "document-1",
            "publicatie": str(publication.uuid),
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "creatiedatum": "2024-01-01",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 0,
            "registratiedatum": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "bestandsdelen": None,
            "documenthandelingen": documenthandelingen,
        }

        self.assertEqual(data, expected_data)

    def test_read_endpoints_document_registered_in_documenten_api(self):
        document = DocumentFactory.create(with_registered_document=True)

        with self.subTest("list endpoint"):
            endpoint = reverse("api:document-list")

            response = self.client.get(endpoint, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # avoid hitting the documenten API for list endpoints
            self.assertIsNone(response.json()["results"][0]["bestandsdelen"])

        with self.subTest("detail endpoint"):
            detail_url = reverse(
                "api:document-detail",
                kwargs={"uuid": str(document.uuid)},
            )

            response = self.client.get(detail_url, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # avoid hitting the documenten API for retrieve operations
            self.assertIsNone(response.json()["bestandsdelen"])


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class DocumentApiCreateTests(VCRMixin, TokenAuthMixin, APITestCase):
    """
    Test the Document create (POST) endpoint.

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

    The flow of requests is quite complex here in this test setup - an alternative
    setup with live server test case would also work, but that's trading one flavour
    of complexity for another (and it's quite a bit slower + harder to debug issues).
    The diagram below describes which requests are handled by which part. The parts
    are:

    * TestClient: ``self.client`` in this test case
    * Woo-P: the code/api endpoints being tested, what we're used to in DRF testing
    * Docker Open Zaak: the Open Zaak instance from the root docker-compose.yml
    * Docker Woo-P: the Woo-P instance from the root docker-compose.yml. Most notably,
      this is the same component but a different instance of Woo-P.

    .. code-block:: none

        TestClient::document-create -> Woo-P:DRF endpoint  ------------+
                                                                       |
        +--- Docker Open Zaak::enkelvoudiginformatieobject-create  <---+
        |
        +--> Docker Woo-P::informatieobjecttype-read
    """

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
        config.organisation_rsin = "000000000"
        config.save()

        cls.information_category = InformationCategoryFactory.create(
            uuid=cls.DOCUMENT_TYPE_UUID
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def _get_vcr_kwargs(self, **kwargs):
        kwargs.setdefault("ignore_hosts", ("invalid-domain",))
        return super()._get_vcr_kwargs(**kwargs)

    def test_create_document_results_in_document_in_external_api(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category],
            verantwoordelijke=organisation,
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "publicatiestatus": PublicationStatusOptions.published,
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "verkorteTitel": "Testdocument",
            "omschrijving": "Testing 123",
            "creatiedatum": "2024-11-05",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 10,
            "documenthandelingen": [
                {
                    "soortHandeling": DocumentActionTypeOptions.signed,
                }
            ],
        }

        with freeze_time("2024-11-13T15:00:00-00:00"):
            response = self.client.post(
                endpoint,
                data=body,
                headers={
                    **AUDIT_HEADERS,
                    "Host": "host.docker.internal:8000",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("documenthandelingen is succesfully created."):
            self.assertEqual(
                response.json()["documenthandelingen"],
                [
                    {
                        "soortHandeling": DocumentActionTypeOptions.signed,
                        "atTime": "2024-11-13T16:00:00+01:00",
                        "wasAssciatedWith": str(organisation.uuid),
                    }
                ],
            )

        with self.subTest("expected woo-publications state"):
            document = Document.objects.get()
            self.assertNotEqual(document.lock, "")
            self.assertEqual(document.document_service, self.service)
            self.assertIsNotNone(document.document_uuid)

            # check that we have one file part in the response
            file_parts = response.json()["bestandsdelen"]
            self.assertEqual(len(file_parts), 1)
            file_part_url = file_parts[0]["url"]
            self.assertEqual(
                file_part_url,
                "http://host.docker.internal:8000/api/v1/documenten/"
                f"{document.uuid}/bestandsdelen/{file_parts[0]["uuid"]}",
            )

        # check that we can look up the document in the Open Zaak API:
        with (
            self.subTest("expected documents API state"),
            get_client(document.document_service) as client,
        ):
            detail = client.get(
                f"enkelvoudiginformatieobjecten/{document.document_uuid}"
            )
            self.assertEqual(detail.status_code, status.HTTP_200_OK)
            detail_data = detail.json()
            self.assertTrue(detail_data["locked"])

    def test_create_document_without_document_handelingen_saves_with_default_options(
        self,
    ):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category],
            verantwoordelijke=organisation,
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "publicatiestatus": PublicationStatusOptions.published,
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "verkorteTitel": "Testdocument",
            "omschrijving": "Testing 123",
            "creatiedatum": "2024-11-05",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 10,
        }

        with freeze_time("2024-11-13T14:00:00+01:00"):
            response = self.client.post(
                endpoint,
                data=body,
                headers={
                    **AUDIT_HEADERS,
                    "Host": "host.docker.internal:8000",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()

        with self.subTest("documenthandelingen is succesfully created."):
            self.assertEqual(
                data["documenthandelingen"],
                [
                    {
                        "soortHandeling": DocumentActionTypeOptions.declared,
                        "atTime": data["registratiedatum"],
                        "wasAssciatedWith": str(organisation.uuid),
                    }
                ],
            )

    def test_create_revoked_document_results_in_error(self):
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category]
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "publicatiestatus": PublicationStatusOptions.revoked,
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "verkorteTitel": "Testdocument",
            "omschrijving": "Testing 123",
            "creatiedatum": "2024-11-05",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 10,
        }

        response = self.client.post(
            endpoint,
            data=body,
            headers={
                **AUDIT_HEADERS,
                "Host": "host.docker.internal:8000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()

        self.assertEqual(
            response_data["publicatiestatus"],
            [
                _("You cannot create a {revoked} document.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                )
            ],
        )

    def test_create_document_with_multiple_handelingen_results_in_error(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category],
            verantwoordelijke=organisation,
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "publicatiestatus": PublicationStatusOptions.published,
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "verkorteTitel": "Testdocument",
            "omschrijving": "Testing 123",
            "creatiedatum": "2024-11-05",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 10,
            "documenthandelingen": [
                {
                    "soortHandeling": DocumentActionTypeOptions.signed,
                    "atTime": "2024-11-13T14:00:00+01:00",
                },
                {
                    "soortHandeling": DocumentActionTypeOptions.signed,
                    "atTime": "2024-11-13T14:00:00+01:00",
                },
            ],
        }

        response = self.client.post(
            endpoint,
            data=body,
            headers={
                **AUDIT_HEADERS,
                "Host": "host.docker.internal:8000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = response.json()

        self.assertEqual(
            data["documenthandelingen"]["nonFieldErrors"],
            ["Ensure this field has no more than 1 elements."],
        )

    def test_upload_file_parts(self):
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )
        assert document.zgw_document is not None
        endpoint = reverse(
            "api:document-filepart-detail",
            kwargs={
                "uuid": document.uuid,
                "part_uuid": document.zgw_document.file_parts[0].uuid,
            },
        )

        response = self.client.put(
            endpoint,
            data={"inhoud": SimpleUploadedFile("dummy.txt", b"aAaAa")},
            format="multipart",
            headers={
                **AUDIT_HEADERS,
                "Host": "host.docker.internal:8000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["documentUploadVoltooid"])

        with get_client(document.document_service) as client:
            with self.subTest("expected documents API state"):
                detail = client.get(
                    f"enkelvoudiginformatieobjecten/{document.document_uuid}"
                )
                self.assertEqual(detail.status_code, status.HTTP_200_OK)
                detail_data = detail.json()
                self.assertFalse(detail_data["locked"])
                self.assertEqual(detail_data["bestandsdelen"], [])

            with self.subTest("expected file content"):
                file_response = client.get(
                    f"enkelvoudiginformatieobjecten/{document.document_uuid}/download"
                )

                self.assertEqual(file_response.status_code, status.HTTP_200_OK)
                # read the binary data and check that it matches what we uploaded
                self.assertEqual(file_response.content, b"aAaAa")

    def test_upload_with_multiple_parts(self):
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=105,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )
        assert document.zgw_document is not None
        endpoint = reverse(
            "api:document-filepart-detail",
            kwargs={
                "uuid": document.uuid,
                "part_uuid": document.zgw_document.file_parts[0].uuid,
            },
        )

        response = self.client.put(
            endpoint,
            data={"inhoud": SimpleUploadedFile("dummy.txt", b"A" * 100)},
            format="multipart",
            headers={
                **AUDIT_HEADERS,
                "Host": "host.docker.internal:8000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["documentUploadVoltooid"])

        with get_client(document.document_service) as client:
            with self.subTest("expected documents API state"):
                detail = client.get(
                    f"enkelvoudiginformatieobjecten/{document.document_uuid}"
                )
                self.assertEqual(detail.status_code, status.HTTP_200_OK)
                detail_data = detail.json()
                self.assertTrue(detail_data["locked"])
                self.assertEqual(len(detail_data["bestandsdelen"]), 2)

    def test_upload_wrong_chunk_size(self):
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )
        assert document.zgw_document is not None
        endpoint = reverse(
            "api:document-filepart-detail",
            kwargs={
                "uuid": document.uuid,
                "part_uuid": document.zgw_document.file_parts[0].uuid,
            },
        )

        response = self.client.put(
            endpoint,
            data={"inhoud": SimpleUploadedFile("dummy.txt", b"aAa")},  # missing 2 bytes
            format="multipart",
            headers={
                **AUDIT_HEADERS,
                "Host": "host.docker.internal:8000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # the error response shape check is deliberately omitted - we're not sure if
        # we should transform the errors or not, so we leave this as undefined behaviour
        # for the time being

    def test_upload_service_not_reachable(self):
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )
        assert document.zgw_document is not None
        endpoint = reverse(
            "api:document-filepart-detail",
            kwargs={
                "uuid": document.uuid,
                "part_uuid": document.zgw_document.file_parts[0].uuid,
            },
        )
        # deliberately break the service configuration to trigger errors
        self.service.api_root = "http://invalid-domain:42000/api/root"
        self.service.save()

        with self.assertRaises(ConnectionError):
            self.client.put(
                endpoint,
                data={"inhoud": SimpleUploadedFile("dummy.txt", b"aAaAa")},
                format="multipart",
                headers={
                    **AUDIT_HEADERS,
                    "Host": "host.docker.internal:8000",
                },
            )

    def test_upload_service_returns_error_response(self):
        document: Document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )
        assert document.zgw_document is not None
        endpoint = reverse(
            "api:document-filepart-detail",
            kwargs={
                "uuid": document.uuid,
                "part_uuid": document.zgw_document.file_parts[0].uuid,
            },
        )
        # deliberately break the service configuration to trigger errors
        self.service.client_id = "invalid-client-id"
        self.service.save()

        with self.assertRaises(HTTPError):
            self.client.put(
                endpoint,
                data={"inhoud": SimpleUploadedFile("dummy.txt", b"aAaAa")},
                format="multipart",
                headers={
                    **AUDIT_HEADERS,
                    "Host": "host.docker.internal:8000",
                },
            )


class DocumentDownloadTests(VCRMixin, TokenAuthMixin, APITestCase):
    """
    Test the Document download (GET) endpoint.

    WOO Publications acts as a bit of a proxy - a document that gets created/registered
    with us is saved into the Documents API, primarily to handle the file uploads
    accordingly.

    The API traffic is captured and 'mocked' using VCR.py. When re-recording the cassettes
    for these tests, make sure to bring up the docker compose in the root of the repo:

    .. code-block:: bash

        docker compose up

    See ``docker/open-zaak/README.md`` for the test credentials and available data.
    """

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
        config.organisation_rsin = "000000000"
        config.save()

        cls.information_category = InformationCategoryFactory.create(
            uuid=cls.DOCUMENT_TYPE_UUID
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_download_document(self):
        document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )
        assert document.zgw_document is not None
        document.upload_part_data(
            uuid=document.zgw_document.file_parts[0].uuid,
            file=SimpleUploadedFile("dummy.txt", b"aAaAa"),
        )
        endpoint = reverse("api:document-download", kwargs={"uuid": document.uuid})

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assert isinstance(response, StreamingHttpResponse)
        self.assertTrue(response.streaming)
        self.assertEqual(response["Content-Length"], "5")

        assert isinstance(response.streaming_content, Iterator)
        content = b"".join(response.streaming_content)
        self.assertEqual(content, b"aAaAa")

    def test_download_incomplete_document(self):
        document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )

        endpoint = reverse("api:document-download", kwargs={"uuid": document.uuid})

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
