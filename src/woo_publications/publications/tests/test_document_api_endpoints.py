from collections.abc import Iterator
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import StreamingHttpResponse
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from freezegun import freeze_time
from requests.exceptions import ConnectionError
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.models import OrganisationMember
from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.api.tests.mixins import (
    APIKeyUnAuthorizedMixin,
    APITestCaseMixin,
    TokenAuthMixin,
)
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.api import DUMMY_IC_UUID
from woo_publications.contrib.documents_api.client import DocumentsAPIError, get_client
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy
from woo_publications.metadata.constants import InformationCategoryOrigins
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)
from woo_publications.utils.tests.vcr import VCRMixin

from ..constants import DocumentDeliveryMethods, PublicationStatusOptions
from ..models import Document, DocumentIdentifier
from .factories import DocumentFactory, DocumentIdentifierFactory, PublicationFactory

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

        with self.subTest(action="put"):
            response = self.client.put(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="patch"):
            response = self.client.patch(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="post"):
            response = self.client.post(detail_endpoint, headers={})

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
        self.assertWrongApiKeyProhibitsPutEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPatchEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPostEndpointAccess(list_url)


class DocumentApiReadTestsCase(TokenAuthMixin, APITestCaseMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=AUDIT_HEADERS["AUDIT_USER_ID"],
            naam=AUDIT_HEADERS["AUDIT_USER_REPRESENTATION"],
        )

    def test_list_documents(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(verantwoordelijke=organisation)
        publication2 = PublicationFactory.create(verantwoordelijke=None)
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
                datum_ondertekend=None,
                ontvangstdatum=timezone.now(),
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            document2 = DocumentFactory.create(
                publicatie=publication2,
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                creatiedatum="2024-02-02",
                datum_ondertekend=timezone.now(),
                ontvangstdatum=None,
            )

        response = self.client.get(reverse("api:document-list"), headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

        with self.subTest("first_item_in_response_with_expected_data"):
            expected_second_item_data = {
                "uuid": str(document2.uuid),
                "identifier": "document-2",
                "publicatie": str(publication2.uuid),
                "kenmerken": [],
                "officieleTitel": "title two",
                "verkorteTitel": "two",
                "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                "publicatiestatus": PublicationStatusOptions.published,
                "creatiedatum": "2024-02-02",
                "bestandsformaat": "unknown",
                "bestandsnaam": "unknown.bin",
                "bestandsomvang": 0,
                "eigenaar": {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "ontvangstdatum": None,
                "datumOndertekend": "2024-09-24T14:00:00+02:00",
                "gepubliceerdOp": "2024-09-24T14:00:00+02:00",
                "ingetrokkenOp": None,
                "uploadVoltooid": False,
            }

            self.assertEqual(data["results"][0], expected_second_item_data)

        with self.subTest("second_item_in_response_with_expected_data"):
            expected_first_item_data = {
                "uuid": str(document.uuid),
                "identifier": "document-1",
                "publicatie": str(publication.uuid),
                "kenmerken": [],
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing "
                "elit.",
                "publicatiestatus": PublicationStatusOptions.published,
                "creatiedatum": "2024-01-01",
                "bestandsformaat": "unknown",
                "bestandsnaam": "unknown.bin",
                "bestandsomvang": 0,
                "eigenaar": {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
                "registratiedatum": "2024-09-25T14:30:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
                "ontvangstdatum": "2024-09-25T14:30:00+02:00",
                "datumOndertekend": None,
                "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
                "ingetrokkenOp": None,
                "uploadVoltooid": False,
            }

            self.assertEqual(data["results"][1], expected_first_item_data)

    def test_list_documents_filter_owner(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(verantwoordelijke=organisation)
        publication2 = PublicationFactory.create(verantwoordelijke=None)
        org_member_1 = OrganisationMemberFactory.create(identifier="123", naam="blauw")
        org_member_2 = OrganisationMemberFactory.create(identifier="456", naam="groen")
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                eigenaar=org_member_1,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            DocumentFactory.create(
                publicatie=publication2,
                eigenaar=org_member_2,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                creatiedatum="2024-02-02",
            )

        with self.subTest("filter with existing eigenaar"):
            response = self.client.get(
                reverse("api:document-list"),
                {"eigenaar": "123"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(document.uuid))

        with self.subTest("filter with none existing eigenaar"):
            response = self.client.get(
                reverse("api:document-list"),
                {"eigenaar": "789"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(response.json()["count"], 0)

        with self.subTest("filter with no input"):
            response = self.client.get(
                reverse("api:document-list"),
                {"eigenaar": ""},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 2)

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
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
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
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            DocumentFactory.create(
                publicatie=publication2,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-2",
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
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
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
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
            publicatie__publicatiestatus=PublicationStatusOptions.published,
            publicatiestatus=PublicationStatusOptions.published,
        )
        concept = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.concept,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        revoked = DocumentFactory.create(
            publicatie__revoked=True,
            publicatiestatus=PublicationStatusOptions.revoked,
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

        with self.subTest("filter on multiple status choices"):
            response = self.client.get(
                list_url,
                {
                    "publicatiestatus": ",".join(
                        (
                            PublicationStatusOptions.published,
                            PublicationStatusOptions.revoked,
                        )
                    )
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(published.uuid))
            self.assertItemInResults(data["results"], "uuid", str(revoked.uuid))

    def test_list_documents_filter_registratie_datum(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            document = DocumentFactory.create()
        with freeze_time("2024-09-25T12:00:00-00:00"):
            document2 = DocumentFactory.create()
        with freeze_time("2024-09-26T12:00:00-00:00"):
            document3 = DocumentFactory.create()

        list_url = reverse("api:document-list")

        with self.subTest("gte specific tests"):
            with self.subTest("filter on gte date is exact match"):
                response = self.client.get(
                    list_url,
                    {"registratiedatumVanaf": "2024-09-26T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document3.uuid))

            with self.subTest("filter on gte date is greater then publication"):
                response = self.client.get(
                    list_url,
                    {"registratiedatumVanaf": "2024-09-26T00:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document3.uuid))

        with self.subTest("lt specific tests"):
            with self.subTest("filter on lt date is exact match"):
                response = self.client.get(
                    list_url,
                    {"registratiedatumTot": "2024-09-24T12:00:01-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document.uuid))

        with self.subTest("lte specific tests"):
            with self.subTest("filter on lt date is exact match"):
                response = self.client.get(
                    list_url,
                    {"registratiedatumTotEnMet": "2024-09-24T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertItemInResults(data["results"], "uuid", str(document.uuid), 1)

            with self.subTest("date is not exact"):
                with self.subTest("filter on lte date is exact match"):
                    response = self.client.get(
                        list_url,
                        {"registratiedatumTotEnMet": "2024-09-25T12:00:00-00:00"},
                        headers=AUDIT_HEADERS,
                    )

                    self.assertEqual(response.status_code, status.HTTP_200_OK)

                    data = response.json()

                    self.assertEqual(data["count"], 2)
                    self.assertItemInResults(
                        data["results"], "uuid", str(document.uuid), 1
                    )
                    self.assertItemInResults(
                        data["results"], "uuid", str(document2.uuid), 1
                    )

        with self.subTest(
            "filter both lt and gte to find publication between two dates"
        ):
            response = self.client.get(
                list_url,
                {
                    "registratiedatumVanaf": "2024-09-25T00:00:00-00:00",
                    "registratiedatumTot": "2024-09-26T00:00:00-00:00",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(document2.uuid))

        with self.subTest("filter both lte and gte to find document between two dates"):
            response = self.client.get(
                list_url,
                {
                    "registratiedatumVanaf": "2024-09-25T12:00:00-00:00",
                    "registratiedatumTotEnMet": "2024-09-25T12:00:00-00:00",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(document2.uuid), 1)

    def test_list_documents_filter_creatie_datum(self):
        document = DocumentFactory.create(creatiedatum="2024-09-24")
        document2 = DocumentFactory.create(creatiedatum="2024-09-25")
        DocumentFactory.create(creatiedatum="2024-09-26")
        document4 = DocumentFactory.create(creatiedatum="2024-09-28")

        list_url = reverse("api:document-list")

        with self.subTest("gte specific tests"):
            with self.subTest("filter on gte date is exact match"):
                response = self.client.get(
                    list_url,
                    {"creatiedatumVanaf": "2024-09-28"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document4.uuid))

            with self.subTest("filter on gte date is greater then publication"):
                response = self.client.get(
                    list_url,
                    {"creatiedatumVanaf": "2024-09-27"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document4.uuid))

        with self.subTest("lt specific tests"):
            with self.subTest("filter on lt date is lesser then publication"):
                response = self.client.get(
                    list_url,
                    {"creatiedatumTot": "2024-09-25"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document.uuid))

        with self.subTest("lte specific tests"):
            with self.subTest("filter on lte date is exact match"):
                response = self.client.get(
                    list_url,
                    {"creatiedatumTotEnMet": "2024-09-24"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertItemInResults(data["results"], "uuid", str(document.uuid), 1)

            with self.subTest("date is not exact"):
                with self.subTest("filter on lte date is exact match"):
                    response = self.client.get(
                        list_url,
                        {"creatiedatumTotEnMet": "2024-09-25"},
                        headers=AUDIT_HEADERS,
                    )

                    self.assertEqual(response.status_code, status.HTTP_200_OK)

                    data = response.json()

                    self.assertEqual(data["count"], 2)
                    self.assertItemInResults(
                        data["results"], "uuid", str(document.uuid), 1
                    )
                    self.assertItemInResults(
                        data["results"], "uuid", str(document2.uuid), 1
                    )

        with self.subTest(
            "filter both lt and gte to find publication between two dates"
        ):
            response = self.client.get(
                list_url,
                {
                    "creatiedatumVanaf": "2024-09-25",
                    "creatiedatumTot": "2024-09-26",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(document2.uuid))

        with self.subTest("filter both lte and gte to find document between two dates"):
            response = self.client.get(
                list_url,
                {
                    "creatiedatumVanaf": "2024-09-25",
                    "creatiedatumTotEnMet": "2024-09-25",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(document2.uuid), 1)

    def test_list_documents_filter_laatst_gewijzigd_datum(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            document = DocumentFactory.create()
        with freeze_time("2024-09-25T12:00:00-00:00"):
            document2 = DocumentFactory.create()
        with freeze_time("2024-09-26T12:00:00-00:00"):
            document3 = DocumentFactory.create()

        list_url = reverse("api:document-list")

        with self.subTest("gte specific tests"):
            with self.subTest("filter on gte date is exact match"):
                response = self.client.get(
                    list_url,
                    {"laatstGewijzigdDatumVanaf": "2024-09-26T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document3.uuid))

            with self.subTest("filter on gte date is greater then publication"):
                response = self.client.get(
                    list_url,
                    {"laatstGewijzigdDatumVanaf": "2024-09-26T00:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document3.uuid))

        with self.subTest("lt specific tests"):
            with self.subTest("filter on lt date is lesser then publication"):
                response = self.client.get(
                    list_url,
                    {"laatstGewijzigdDatumTot": "2024-09-25T00:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(document.uuid))

        with self.subTest("lte specific tests"):
            with self.subTest("filter on lte date is exact match"):
                response = self.client.get(
                    list_url,
                    {"laatstGewijzigdDatumTotEnMet": "2024-09-24T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertItemInResults(data["results"], "uuid", str(document.uuid), 1)

            with self.subTest("date is not exact"):
                with self.subTest("filter on lte date is exact match"):
                    response = self.client.get(
                        list_url,
                        {"laatstGewijzigdDatumTotEnMet": "2024-09-25T12:00:00-00:00"},
                        headers=AUDIT_HEADERS,
                    )

                    self.assertEqual(response.status_code, status.HTTP_200_OK)

                    data = response.json()

                    self.assertEqual(data["count"], 2)
                    self.assertItemInResults(
                        data["results"], "uuid", str(document.uuid), 1
                    )
                    self.assertItemInResults(
                        data["results"], "uuid", str(document2.uuid), 1
                    )

        with self.subTest(
            "filter both lt and gte to find publication between two dates"
        ):
            response = self.client.get(
                list_url,
                {
                    "laatstGewijzigdDatumVanaf": "2024-09-25T00:00:00-00:00",
                    "laatstGewijzigdDatumTot": "2024-09-26T00:00:00-00:00",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(document2.uuid))

        with self.subTest(
            "filter both lte and gte to find publication between two dates"
        ):
            response = self.client.get(
                list_url,
                {
                    "laatstGewijzigdDatumVanaf": "2024-09-25T12:00:00-00:00",
                    "laatstGewijzigdDatumTotEnMet": "2024-09-25T12:00:00-00:00",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(document2.uuid), 1)

    def test_list_document_filter_information_categories(self):
        ic, ic2, ic3, ic4 = InformationCategoryFactory.create_batch(
            4, oorsprong=InformationCategoryOrigins.value_list
        )
        (
            custom_ic,
            custom_ic2,
        ) = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.custom_entry
        )
        inspanningsverplichting_ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list,
            identifier=settings.INSPANNINGSVERPLICHTING_IDENTIFIER,
        )
        publication = PublicationFactory.create(informatie_categorieen=[ic])
        publication2 = PublicationFactory.create(informatie_categorieen=[ic2])
        publication3 = PublicationFactory.create(informatie_categorieen=[ic3, ic4])
        publication4 = PublicationFactory.create(informatie_categorieen=[custom_ic])
        publication5 = PublicationFactory.create(informatie_categorieen=[custom_ic2])
        publication6 = PublicationFactory.create(
            informatie_categorieen=[inspanningsverplichting_ic]
        )
        document = DocumentFactory.create(publicatie=publication)
        document2 = DocumentFactory.create(publicatie=publication2)
        document3 = DocumentFactory.create(publicatie=publication3)
        document4 = DocumentFactory.create(publicatie=publication4)
        document5 = DocumentFactory.create(publicatie=publication5)
        document6 = DocumentFactory.create(publicatie=publication6)

        list_url = reverse("api:document-list")

        with self.subTest("filter on a single information category"):
            response = self.client.get(
                list_url,
                {"informatieCategorieen": str(ic.uuid)},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(document.uuid), 1)

        with self.subTest("filter on multiple information categories "):
            response = self.client.get(
                list_url,
                {"informatieCategorieen": f"{ic2.uuid},{ic4.uuid}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(document2.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(document3.uuid), 1)

        with self.subTest("filter on the insappingsverplichting category"):
            response = self.client.get(
                list_url,
                {"informatieCategorieen": f"{inspanningsverplichting_ic.uuid}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 3)
            self.assertItemInResults(data["results"], "uuid", str(document4.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(document5.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(document6.uuid), 1)

        with self.subTest("filter with invalid uuid"):
            fake_ic = uuid4()
            response = self.client.get(
                list_url,
                {"informatieCategorieen": f"{fake_ic}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            data = response.json()
            error_message = _(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {"value": str(fake_ic)}

            self.assertEqual(data["informatieCategorieen"], [error_message])

    def test_detail_document(self):
        publication = PublicationFactory.create()
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                eigenaar=self.organisation_member,
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

        expected_data = {
            "uuid": str(document.uuid),
            "identifier": "document-1",
            "publicatie": str(publication.uuid),
            "kenmerken": [],
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "creatiedatum": "2024-01-01",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 0,
            "eigenaar": {
                "identifier": self.organisation_member.identifier,
                "weergaveNaam": self.organisation_member.naam,
            },
            "registratiedatum": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "ontvangstdatum": None,
            "datumOndertekend": None,
            "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
            "ingetrokkenOp": None,
            "uploadVoltooid": False,
        }

        self.assertEqual(data, expected_data)

    def test_read_endpoints_document_registered_in_documenten_api(self):
        document = DocumentFactory.create(with_registered_document=True)

        with self.subTest("list endpoint"):
            endpoint = reverse("api:document-list")

            response = self.client.get(endpoint, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # avoid hitting the documenten API for list endpoints
            self.assertNotIn("bestandsdelen", response.json()["results"][0])

        with self.subTest("detail endpoint"):
            detail_url = reverse(
                "api:document-detail",
                kwargs={"uuid": str(document.uuid)},
            )

            response = self.client.get(detail_url, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # avoid hitting the documenten API for retrieve operations
            self.assertNotIn("bestandsdelen", response.json())


class DocumentApiMetaDataUpdateTests(TokenAuthMixin, APITestCase):
    @patch("woo_publications.publications.tasks.index_document.delay")
    def test_update_document_schedules_index_update_task(
        self,
        mock_index_document_delay: MagicMock,
    ):
        document = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.published,
            publicatiestatus=PublicationStatusOptions.published,
            identifier="document-1",
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            creatiedatum="2024-01-01",
        )

        body = {
            "officieleTitel": "changed officiele_title",
            "verkorteTitel": "changed verkorte_title",
            "omschrijving": "changed omschrijving",
            "publicatiestatus": PublicationStatusOptions.published,
            "creatiedatum": "2008-02-23",
            "ontvangstdatum": "2024-09-25T14:30:00+02:00",
            "datumOndertekend": "2024-09-25T14:30:00+02:00",
        }

        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.put(detail_url, data=body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(response_data["officieleTitel"], "changed officiele_title")
        self.assertEqual(response_data["verkorteTitel"], "changed verkorte_title")
        self.assertEqual(response_data["omschrijving"], "changed omschrijving")
        self.assertEqual(response_data["ontvangstdatum"], "2024-09-25T14:30:00+02:00")
        self.assertEqual(response_data["datumOndertekend"], "2024-09-25T14:30:00+02:00")
        self.assertEqual(
            response_data["publicatiestatus"], PublicationStatusOptions.published
        )
        self.assertEqual(response_data["creatiedatum"], "2008-02-23")
        download_path = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )
        mock_index_document_delay.assert_called_once_with(
            document_id=document.pk, download_url=f"http://testserver{download_path}"
        )

    def test_partial_update_document(self):
        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            identifier="document-1",
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            creatiedatum="2024-01-01",
        )

        body = {
            "officieleTitel": "changed officiele_title",
        }

        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        response = self.client.patch(detail_url, data=body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()

        self.assertEqual(response_data["officieleTitel"], "changed officiele_title")

    def test_partial_update_document_eigenaar(self):
        org_member_1 = OrganisationMemberFactory.create(
            identifier="test-identifier", naam="test-naam"
        )
        document = DocumentFactory.create(
            eigenaar=org_member_1,
            publicatiestatus=PublicationStatusOptions.published,
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

        with self.subTest("update document with new owner"):
            self.assertFalse(
                OrganisationMember.objects.filter(
                    identifier="new-owner-identifier",
                    naam="new-owner-naam",
                ).exists()
            )
            body = {
                "eigenaar": {
                    "identifier": "new-owner-identifier",
                    "weergaveNaam": "new-owner-naam",
                },
            }

            response = self.client.patch(detail_url, data=body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()

            self.assertEqual(
                response_data["eigenaar"],
                {
                    "identifier": "new-owner-identifier",
                    "weergaveNaam": "new-owner-naam",
                },
            )
            self.assertTrue(
                OrganisationMember.objects.filter(
                    identifier="new-owner-identifier",
                    naam="new-owner-naam",
                ).exists()
            )

        with self.subTest("update document with existing owner"):
            body = {
                "eigenaar": {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            }

            response = self.client.patch(detail_url, data=body, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response_data = response.json()

            self.assertEqual(
                response_data["eigenaar"],
                {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            )
            # No new OrganisationMember got created.
            self.assertEqual(
                OrganisationMember.objects.filter(
                    identifier="new-owner-identifier",
                    naam="new-owner-naam",
                ).count(),
                1,
            )

    def test_partial_publication_kenmerken(self):
        document = DocumentFactory.create()
        DocumentIdentifierFactory.create(
            document=document, kenmerk="kenmerk 1", bron="bron 1"
        )
        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        with self.subTest("kenmerken not provided"):
            data = {
                "officieleTitel": "bla",
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()

            self.assertEqual(
                response_data["kenmerken"], [{"kenmerk": "kenmerk 1", "bron": "bron 1"}]
            )
            self.assertTrue(
                DocumentIdentifier.objects.filter(
                    document=document, kenmerk="kenmerk 1", bron="bron 1"
                ).exists()
            )

        with self.subTest("updating kenmerken"):
            data = {
                "kenmerken": [
                    {"kenmerk": "kenmerk 1", "bron": "bron 1"},
                    {"kenmerk": "kenmerk 2", "bron": "bron 2"},
                ]
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()

            self.assertEqual(
                response_data["kenmerken"],
                [
                    {"kenmerk": "kenmerk 1", "bron": "bron 1"},
                    {"kenmerk": "kenmerk 2", "bron": "bron 2"},
                ],
            )
            self.assertTrue(
                DocumentIdentifier.objects.filter(
                    document=document, kenmerk="kenmerk 1", bron="bron 1"
                ).exists()
            )
            self.assertTrue(
                DocumentIdentifier.objects.filter(
                    document=document, kenmerk="kenmerk 2", bron="bron 2"
                ).exists()
            )

        with self.subTest("updating kenmerken empty array"):
            data = {"kenmerken": []}

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()

            self.assertEqual(response_data["kenmerken"], [])
            self.assertFalse(
                DocumentIdentifier.objects.filter(
                    document=document, kenmerk="kenmerk 1", bron="bron 1"
                ).exists()
            )
            self.assertFalse(
                DocumentIdentifier.objects.filter(
                    document=document, kenmerk="kenmerk 2", bron="bron 2"
                ).exists()
            )

    def test_partial_update_kenmerken_validation(self):
        document = DocumentFactory.create()
        document2 = DocumentFactory.create()
        DocumentIdentifierFactory.create(
            document=document, kenmerk="kenmerk 1", bron="bron 1"
        )
        DocumentIdentifierFactory.create(
            document=document, kenmerk="kenmerk 2", bron="bron 2"
        )
        with self.subTest("validate duplicated items given"):
            url = reverse(
                "api:document-detail",
                kwargs={"uuid": str(document.uuid)},
            )
            data = {
                "kenmerken": [
                    {"kenmerk": "new kenmerk", "bron": "new bron"},
                    {"kenmerk": "new kenmerk", "bron": "new bron"},
                ]
            }

            response = self.client.patch(url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            self.assertEqual(
                response.json()["kenmerken"],
                [_("You cannot provide identical identifiers.")],
            )

        with self.subTest("other publication is allowed to have same item"):
            url = reverse(
                "api:document-detail",
                kwargs={"uuid": str(document2.uuid)},
            )
            data = {
                "kenmerken": [
                    {"kenmerk": "kenmerk 1", "bron": "kenmerk 1"},
                ]
            }

            response = self.client.patch(url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class DocumentApiCreateTests(VCRMixin, TokenAuthMixin, APITestCase):
    """
    Test the Document create (POST) endpoint.

    WOO Publications acts as a bit of a proxy - a document that gets created/registered
    with us is saved into the Documents API, primarily to handle the file uploads
    accordingly.

    The API traffic is captured and 'mocked' using VCR.py. When re-recording the
    cassettes for these tests, make sure to bring up the docker compose in the root of
    the repo:

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

    @patch("woo_publications.publications.api.viewsets.process_source_document.delay")
    def test_create_document_results_in_document_in_external_api(
        self, mock_process_source_document_delay: MagicMock
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
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "verkorteTitel": "Testdocument",
            "omschrijving": "Testing 123",
            "creatiedatum": "2024-11-05",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 10,
        }

        with (
            freeze_time("2024-11-13T15:00:00-00:00"),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(
                endpoint,
                data=body,
                headers={
                    **AUDIT_HEADERS,
                    "Host": "host.docker.internal:8000",
                },
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_process_source_document_delay.assert_not_called()

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
                "http://host.docker.internal:8000/api/v2/documenten/"
                f"{document.uuid}/bestandsdelen/{file_parts[0]['uuid']}",
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

    def test_create_document_download_delivery_ignores_source_url(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category],
            verantwoordelijke=organisation,
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "officieleTitel": "Test document external URL",
            "creatiedatum": "2024-11-05",
            "aanleveringBestand": DocumentDeliveryMethods.receive_upload,
            "documentUrl": "https://example.com/foo",
        }

        response = self.client.post(
            endpoint,
            data=body,
            headers={
                **AUDIT_HEADERS,
                "Host": "host.docker.internal:8000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get()
        self.assertEqual(document.source_url, "")

    def test_create_concept_document_with_a_publication_with_no_ic(self):
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[],
            verantwoordelijke=organisation,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
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

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        document = Document.objects.get()
        with (
            self.subTest("expect IC to be the hardcoded dummy data"),
            get_client(document.document_service) as client,
        ):
            detail = client.get(
                f"enkelvoudiginformatieobjecten/{document.document_uuid}"
            )
            self.assertEqual(detail.status_code, status.HTTP_200_OK)
            detail_data = detail.json()
            self.assertEqual(
                detail_data["informatieobjecttype"],
                f"http://host.docker.internal:8000/catalogi/api/v1/informatieobjecttypen/{DUMMY_IC_UUID}",
            )

    @patch("woo_publications.publications.models.Document.register_in_documents_api")
    def test_create_document_with_custom_owner(
        self, mock_register_in_documents_api: MagicMock
    ):
        self.assertFalse(
            OrganisationMember.objects.filter(
                identifier="test-identifier", naam="test-naam"
            ).exists(),
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category]
        )
        endpoint = reverse("api:document-list")
        body = {
            "publicatie": publication.uuid,
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "creatiedatum": "2024-11-05",
            "eigenaar": {
                "identifier": "test-identifier",
                "weergaveNaam": "test-naam",
            },
        }

        response = self.client.post(
            endpoint,
            data=body,
            headers={
                **AUDIT_HEADERS,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()

        self.assertEqual(
            response_data["eigenaar"],
            {
                "identifier": "test-identifier",
                "weergaveNaam": "test-naam",
            },
        )
        self.assertTrue(
            OrganisationMember.objects.filter(
                identifier="test-identifier", naam="test-naam"
            ).exists(),
        )

    @patch("woo_publications.publications.models.Document.register_in_documents_api")
    def test_create_document_with_inline_kenmerken(
        self, mock_register_in_documents_api: MagicMock
    ):
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category]
        )
        endpoint = reverse("api:document-list")
        body = {
            "publicatie": publication.uuid,
            "officieleTitel": "Testdocument WOO-P + Open Zaak",
            "creatiedatum": "2024-11-05",
            "kenmerken": [
                {"kenmerk": "kenmerk 1", "bron": "bron 1"},
                {"kenmerk": "kenmerk 2", "bron": "bron 2"},
            ],
        }

        response = self.client.post(
            endpoint,
            data=body,
            headers={
                **AUDIT_HEADERS,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()

        created_document = Document.objects.get(uuid=response_data["uuid"])
        self.assertTrue(
            DocumentIdentifier.objects.filter(
                document=created_document, kenmerk="kenmerk 1", bron="bron 1"
            ).exists()
        )
        self.assertTrue(
            DocumentIdentifier.objects.filter(
                document=created_document, kenmerk="kenmerk 2", bron="bron 2"
            ).exists()
        )

    @patch("woo_publications.publications.api.viewsets.index_document.delay")
    def test_upload_file_parts(self, mock_index_document_delay: MagicMock):
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
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )

        with self.captureOnCommitCallbacks(execute=True):
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

        with self.subTest("lock id cleared and flag updated"):
            document.refresh_from_db()

            self.assertEqual(document.lock, "")
            self.assertTrue(document.upload_complete)

        with self.subTest("document index task is scheduled"):
            mock_index_document_delay.assert_called_once_with(
                document_id=document.pk,
                download_url=f"http://host.docker.internal:8000{download_url}",
            )

    @patch("woo_publications.publications.api.viewsets.index_document.delay")
    def test_upload_with_multiple_parts(self, mock_index_document_delay: MagicMock):
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

        with self.captureOnCommitCallbacks(execute=True):
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
        mock_index_document_delay.assert_not_called()

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

        with (
            self.assertRaises(ConnectionError),
            self.vcr_raises(exception=ConnectionError),
        ):
            self.client.put(
                endpoint,
                data={"inhoud": SimpleUploadedFile("dummy.txt", b"aAaAa")},
                format="multipart",
                headers={
                    **AUDIT_HEADERS,
                    "Host": "host.docker.internal:8000",
                },
            )

    @patch("woo_publications.publications.api.viewsets.process_source_document.delay")
    def test_create_document_with_external_document_url(
        self, mock_process_source_document_delay: MagicMock
    ):
        # create an actual document in the remote Open Zaak that we can point to
        with get_client(self.service) as client:
            openzaak_document = client.create_document(
                # must be unique for the source organisation
                identification=str(uuid4()),
                source_organisation="123456782",
                document_type_url=self.DOCUMENT_TYPE_URL,
                creation_date=date.today(),
                title="File part test",
                filesize=10,  # in bytes
                filename="data.txt",
                content_type="text/plain",
            )
        document_url = (
            "http://openzaak.docker.internal:8001/documenten/api/v1/"
            f"enkelvoudiginformatieobjecten/{openzaak_document.uuid}"
            "?versie=1"
        )
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category],
            verantwoordelijke=organisation,
        )
        endpoint = reverse("api:document-list")
        body = {
            "identifier": "WOO-P/0042",
            "publicatie": publication.uuid,
            "officieleTitel": "Test document external URL",
            "creatiedatum": "2024-11-05",
            "aanleveringBestand": DocumentDeliveryMethods.retrieve_url,
            "documentUrl": document_url,
        }

        with self.subTest("successful creation"):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    endpoint,
                    data=body,
                    headers={**AUDIT_HEADERS, "Host": "host.docker.internal:8000"},
                )

            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, response.json()
            )
            data = response.json()
            self.assertIsNone(data["bestandsdelen"])
            self.assertFalse(data["uploadVoltooid"])

            document = Document.objects.get(uuid=data["uuid"])
            mock_process_source_document_delay.assert_called_once_with(
                document_id=document.id,
                base_url="http://host.docker.internal:8000/",
            )

            # check database state - we expect nothing to be done yet because a
            # background task will do the actual processing
            self.assertIsNone(document.document_service)
            self.assertIsNone(document.document_uuid)
            self.assertEqual(document.source_url, document_url)
            self.assertFalse(document.upload_complete)
            self.assertEqual(document.bestandsomvang, 0)  # will be set via Celery!

    def test_create_document_external_document_url_validation(self):
        # create an actual document in the remote Open Zaak that we can point to
        with get_client(self.service) as client:
            openzaak_document = client.create_document(
                # must be unique for the source organisation
                identification=str(uuid4()),
                source_organisation="123456782",
                document_type_url=self.DOCUMENT_TYPE_URL,
                creation_date=date.today(),
                title="Dummy",
                filesize=0,  # in bytes
                filename="data.txt",
                content_type="text/plain",
            )

        document_url = (
            "http://openzaak.docker.internal:8001/documenten/api/v1/"
            f"enkelvoudiginformatieobjecten/{openzaak_document.uuid}"
        )
        organisation = OrganisationFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[self.information_category],
            verantwoordelijke=organisation,
        )
        endpoint = reverse("api:document-list")

        with self.subTest("validate document_url is provided"):
            response = self.client.post(
                endpoint,
                data={
                    "identifier": "WOO-P/0042",
                    "publicatie": publication.uuid,
                    "officieleTitel": "Test document external URL",
                    "creatiedatum": "2024-11-05",
                    "aanleveringBestand": DocumentDeliveryMethods.retrieve_url,
                },
                headers={**AUDIT_HEADERS, "Host": "host.docker.internal:8000"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("document_url", response.data)
            self.assertEqual(response.data["document_url"][0].code, "required")

        with self.subTest("validate document_url is not empty"):
            response = self.client.post(
                endpoint,
                data={
                    "identifier": "WOO-P/0042",
                    "publicatie": publication.uuid,
                    "officieleTitel": "Test document external URL",
                    "creatiedatum": "2024-11-05",
                    "aanleveringBestand": DocumentDeliveryMethods.retrieve_url,
                    "documentUrl": "",
                },
                headers={**AUDIT_HEADERS, "Host": "host.docker.internal:8000"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("document_url", response.data)
            self.assertEqual(response.data["document_url"][0].code, "blank")

        with self.subTest("validate document_url points to known service"):
            response = self.client.post(
                endpoint,
                data={
                    "identifier": "WOO-P/0043",
                    "publicatie": publication.uuid,
                    "officieleTitel": "Test document external URL",
                    "creatiedatum": "2024-11-05",
                    "aanleveringBestand": DocumentDeliveryMethods.retrieve_url,
                    "documentUrl": "https://example.com",
                },
                headers={**AUDIT_HEADERS, "Host": "host.docker.internal:8000"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("document_url", response.data)
            self.assertEqual(response.data["document_url"][0].code, "unknown_service")

        with self.subTest("validate document_url points to document resource"):
            response = self.client.post(
                endpoint,
                data={
                    "identifier": "WOO-P/0044",
                    "publicatie": publication.uuid,
                    "officieleTitel": "Test document external URL",
                    "creatiedatum": "2024-11-05",
                    "aanleveringBestand": DocumentDeliveryMethods.retrieve_url,
                    "documentUrl": f"{document_url}/bad-suffix",
                },
                headers={**AUDIT_HEADERS, "Host": "host.docker.internal:8000"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("document_url", response.data)
            self.assertEqual(response.data["document_url"][0].code, "invalid")

        with self.subTest("validate document_url points to existing version"):
            response = self.client.post(
                endpoint,
                data={
                    "identifier": "WOO-P/0045",
                    "publicatie": publication.uuid,
                    "officieleTitel": "Test document external URL",
                    "creatiedatum": "2024-11-05",
                    "aanleveringBestand": DocumentDeliveryMethods.retrieve_url,
                    "documentUrl": f"{document_url}?versie=999",
                },
                headers={**AUDIT_HEADERS, "Host": "host.docker.internal:8000"},
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("document_url", response.data)
            self.assertEqual(response.data["document_url"][0].code, "does_not_exist")


class DocumentDownloadTests(VCRMixin, TokenAuthMixin, APITestCase):
    """
    Test the Document download (GET) endpoint.

    WOO Publications acts as a bit of a proxy - a document that gets created/registered
    with us is saved into the Documents API, primarily to handle the file uploads
    accordingly.

    The API traffic is captured and 'mocked' using VCR.py. When re-recording the
    cassettes for these tests, make sure to bring up the docker compose in the root of
    the repo:

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
        self.assertIn("Content-Disposition", response)

        assert isinstance(response.streaming_content, Iterator)
        content = b"".join(response.streaming_content)
        self.assertEqual(content, b"aAaAa")

    def test_download_incomplete_document(self):
        document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
            # a lie, but this mimicks a problem on the Documents API side
            upload_complete=True,
        )
        document.register_in_documents_api(
            build_absolute_uri=lambda path: f"http://host.docker.internal:8000{path}",
        )

        endpoint = reverse("api:document-download", kwargs={"uuid": document.uuid})

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_download_document_unfinished_upload(self):
        document = DocumentFactory.create(
            publicatie__informatie_categorieen=[self.information_category],
            bestandsomvang=5,
        )
        assert document.document_service is None
        assert document.document_uuid is None
        endpoint = reverse("api:document-download", kwargs={"uuid": document.uuid})

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


@override_settings(ALLOWED_HOSTS=["testserver", "host.docker.internal"])
class DocumentApiDeleteTests(VCRMixin, TokenAuthMixin, APITestCase):
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

    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    def test_delete_document_no_document_connected(
        self,
        mock_remove_document_from_index: MagicMock,
    ):
        document = DocumentFactory.create(document_service=None, document_uuid=None)
        url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(uuid=document.uuid).exists())
        self.assertEqual(len(self.cassette), 0)
        mock_remove_document_from_index.assert_called_once_with(document_id=document.pk)

    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    def test_delete_document_open_zaak_error(
        self,
        mock_remove_document_from_index: MagicMock,
    ):
        document = DocumentFactory.create(
            document_service=self.service,
            document_uuid=self.DOCUMENT_TYPE_UUID,
            officiele_titel="doc-1",
        )
        url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        with patch(
            "woo_publications.contrib.documents_api.client.DocumentenClient.destroy_document",
            side_effect=DocumentsAPIError(
                message=_("Something went wrong while deleting the document.")
            ),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.json(),
            {"detail": _("Something went wrong while deleting the document.")},
        )
        self.assertTrue(Document.objects.filter(uuid=document.uuid).exists())
        log = TimelineLogProxy.objects.for_object(document).get(  # pyright: ignore[reportAttributeAccessIssue]
            extra_data__event=Events.delete_document
        )
        expected_data = {
            "event": Events.delete_document,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "document_data": {
                "success": False,
                "service_uuid": str(self.service.uuid),
                "document_uuid": str(self.DOCUMENT_TYPE_UUID),
            },
            "_cached_object_repr": "doc-1",
        }
        self.assertEqual(log.extra_data, expected_data)
        mock_remove_document_from_index.assert_called_once_with(document_id=document.pk)

    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    def test_destroy_document_with_no_doc_in_openzaak(
        self, mock_remove_document_from_index: MagicMock
    ):
        none_existing_openzaak_document_uuid = "88d4c4a5-4dd9-454a-9b66-9ad46074012f"
        document = DocumentFactory(
            document_service=self.service,
            document_uuid=none_existing_openzaak_document_uuid,
        )
        url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(uuid=document.uuid).exists())
        self.assertEqual(len(self.cassette), 1)
        self.assertFalse(
            TimelineLogProxy.objects.for_object(document)  # pyright: ignore[reportAttributeAccessIssue]
            .filter(extra_data__event=Events.delete_document)
            .exists()
        )
        mock_remove_document_from_index.assert_called_once_with(document_id=document.pk)

    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    def test_destroy_document_full_flow(
        self, mock_remove_document_from_index: MagicMock
    ):
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

        document = DocumentFactory(
            document_service=self.service, document_uuid=openzaak_document.uuid
        )
        url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(uuid=document.uuid).exists())

        with get_client(self.service) as client:
            openzaak_response = client.get(
                f"enkelvoudiginformatieobjecten/{openzaak_document.uuid}"
            )
            self.assertEqual(openzaak_response.status_code, status.HTTP_404_NOT_FOUND)

        mock_remove_document_from_index.assert_called_once_with(document_id=document.pk)
