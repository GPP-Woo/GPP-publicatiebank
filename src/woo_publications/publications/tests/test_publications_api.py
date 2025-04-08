from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.translation import gettext as _

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import (
    APIKeyUnAuthorizedMixin,
    APITestCaseMixin,
    TokenAuthMixin,
)
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.logging.logevent import audit_api_create
from woo_publications.logging.serializing import serialize_instance
from woo_publications.metadata.constants import InformationCategoryOrigins
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from ..models import Publication
from .factories import DocumentFactory, PublicationFactory, TopicFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class PublicationApiAuthorizationAndPermissionTests(
    APIKeyUnAuthorizedMixin, APITestCase
):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:publication-list")
        detail_endpoint = reverse(
            "api:publication-detail", kwargs={"uuid": str(uuid4())}
        )

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="create"):
            response = self.client.post(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="update"):
            response = self.client.put(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="destroy"):
            response = self.client.delete(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_key_result_in_401_with_wrong_credentials(self):
        publication = PublicationFactory.create()
        list_url = reverse("api:publication-list")
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        # create
        self.assertWrongApiKeyProhibitsPostEndpointAccess(detail_url)
        # read
        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)
        # update
        self.assertWrongApiKeyProhibitsPatchEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPutEndpointAccess(detail_url)
        # delete
        self.assertWrongApiKeyProhibitsDeleteEndpointAccess(detail_url)


class PublicationApiTestsCase(TokenAuthMixin, APITestCaseMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # diWooInformatieCategorieen needs to have inspannings verplichting record in case of custom entries
        cls.inspannings_verplichting = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list,
            identifier=settings.INSPANNINGSVERPLICHTING_IDENTIFIER,
        )

        # the get_inspannings_verplichting func which is called while fetching the diWooInformatieCategorieen data is cached.
        # so we clear the cache after each test to maintain test isolation.
        cls.addClassCleanup(cache.clear)

    def test_list_publications(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )
        topic = TopicFactory.create()
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic],
                onderwerpen=[topic],
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication2 = PublicationFactory.create(
                informatie_categorieen=[ic2],
                publicatiestatus=PublicationStatusOptions.concept,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )

        response = self.client.get(
            reverse("api:publication-list"), headers=AUDIT_HEADERS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

        with self.subTest("first item in response with expected data"):
            expected_first_item_data = {
                "uuid": str(publication.uuid),
                "informatieCategorieen": [str(ic.uuid)],
                "diWooInformatieCategorieen": [str(ic.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(publication.publisher.uuid),
                "verantwoordelijke": None,
                "opsteller": None,
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.published,
                "eigenaar": None,
                "registratiedatum": "2024-09-25T14:30:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
                "bronBewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2025-01-01",
                "toelichtingBewaartermijn": "",
            }

            self.assertEqual(data["results"][0], expected_first_item_data)

        with self.subTest("second item in response with expected_data"):
            expected_second_item_data = {
                "uuid": str(publication2.uuid),
                "informatieCategorieen": [str(ic2.uuid)],
                "diWooInformatieCategorieen": [str(ic2.uuid)],
                "onderwerpen": [],
                "publisher": str(publication2.publisher.uuid),
                "verantwoordelijke": None,
                "opsteller": None,
                "officieleTitel": "title two",
                "verkorteTitel": "two",
                "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                "publicatiestatus": PublicationStatusOptions.concept,
                "eigenaar": None,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "bronBewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2025-01-01",
                "toelichtingBewaartermijn": "",
            }

            self.assertEqual(data["results"][1], expected_second_item_data)

    def test_list_publications_filter_order(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = PublicationFactory.create(
                informatie_categorieen=[ic2],
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        expected_first_item_data = {
            "uuid": str(publication.uuid),
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [],
            "publisher": str(publication.publisher.uuid),
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }
        expected_second_item_data = {
            "uuid": str(publication2.uuid),
            "informatieCategorieen": [str(ic2.uuid)],
            "diWooInformatieCategorieen": [str(ic2.uuid)],
            "onderwerpen": [],
            "publisher": str(publication2.publisher.uuid),
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title two",
            "verkorteTitel": "two",
            "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": None,
            "registratiedatum": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }

        # registratiedatum
        with self.subTest("registratiedatum ascending"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"sorteer": "registratiedatum"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0], expected_first_item_data)
            self.assertEqual(data["results"][1], expected_second_item_data)

        with self.subTest("registratiedatum descending"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"sorteer": "-registratiedatum"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0], expected_second_item_data)
            self.assertEqual(data["results"][1], expected_first_item_data)

        # Officiele titel
        with self.subTest("officiele title ascending"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"sorteer": "officiele_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0], expected_first_item_data)
            self.assertEqual(data["results"][1], expected_second_item_data)

        with self.subTest("officiele title descending"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"sorteer": "-officiele_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0], expected_second_item_data)
            self.assertEqual(data["results"][1], expected_first_item_data)

        # short titel
        with self.subTest("verkorte titel ascending"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"sorteer": "verkorte_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0], expected_first_item_data)
            self.assertEqual(data["results"][1], expected_second_item_data)

        with self.subTest("verkorte titel descending"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"sorteer": "-verkorte_titel"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["results"][0], expected_second_item_data)
            self.assertEqual(data["results"][1], expected_first_item_data)

    def test_list_publications_filter_information_categories(self):
        ic, ic2, ic3, ic4 = InformationCategoryFactory.create_batch(
            4, oorsprong=InformationCategoryOrigins.value_list
        )
        (
            custom_ic,
            custom_ic2,
        ) = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.custom_entry
        )
        publication = PublicationFactory.create(informatie_categorieen=[ic])
        publication2 = PublicationFactory.create(informatie_categorieen=[ic2])
        publication3 = PublicationFactory.create(informatie_categorieen=[ic3, ic4])
        publication4 = PublicationFactory.create(informatie_categorieen=[custom_ic])
        publication5 = PublicationFactory.create(informatie_categorieen=[custom_ic2])
        publication6 = PublicationFactory.create(
            informatie_categorieen=[self.inspannings_verplichting]
        )

        list_url = reverse("api:publication-list")

        with self.subTest("filter on a single information category"):
            response = self.client.get(
                list_url,
                {"informatieCategorieen": str(ic.uuid)},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(publication.uuid), 1)

        with self.subTest("filter on multiple information categories "):
            response = self.client.get(
                list_url,
                {"informatieCategorieen": f"{ic2.uuid},{ic4.uuid}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(publication2.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(publication3.uuid), 1)

        with self.subTest("filter on the insappingsverplichting category"):
            response = self.client.get(
                list_url,
                {"informatieCategorieen": f"{self.inspannings_verplichting.uuid}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 3)
            self.assertItemInResults(data["results"], "uuid", str(publication4.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(publication5.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(publication6.uuid), 1)

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

    def test_list_publications_filter_topic(self):
        topic, topic2, topic3, topic4 = TopicFactory.create_batch(4)

        publication = PublicationFactory.create(onderwerpen=[topic])
        publication2 = PublicationFactory.create(onderwerpen=[topic2])
        publication3 = PublicationFactory.create(onderwerpen=[topic3, topic4])

        list_url = reverse("api:publication-list")

        with self.subTest("filter on a single topic"):
            response = self.client.get(
                list_url,
                {"onderwerpen": str(topic.uuid)},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(publication.uuid), 1)

        with self.subTest("filter on multiple topics"):
            response = self.client.get(
                list_url,
                {"onderwerpen": f"{topic2.uuid},{topic3.uuid}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(publication2.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(publication3.uuid), 1)

        with self.subTest("filter with invalid uuid"):
            fake_topic = uuid4()
            response = self.client.get(
                list_url,
                {"onderwerpen": f"{fake_topic}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            data = response.json()
            error_message = _(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {"value": str(fake_topic)}

            self.assertEqual(data["onderwerpen"], [error_message])

    def test_list_publications_filter_registratie_datum(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(informatie_categorieen=[ic])
        with freeze_time("2024-09-25T12:00:00-00:00"):
            publication2 = PublicationFactory.create(informatie_categorieen=[ic])
        with freeze_time("2024-09-26T12:00:00-00:00"):
            publication3 = PublicationFactory.create(informatie_categorieen=[ic])

        with self.subTest("gte specific tests"):
            with self.subTest("filter on gte date is exact match"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"registratiedatumVanaf": "2024-09-26T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(publication3.uuid))

            with self.subTest("filter on gte date is greater then publication"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"registratiedatumVanaf": "2024-09-26T00:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(publication3.uuid))

        with self.subTest("lt specific tests"):
            with self.subTest("filter on lt date is lesser then publication"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"registratiedatumTot": "2024-09-25T00:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(publication.uuid))

        with self.subTest("lte specific tests"):
            with self.subTest("filter on lt date is exact match"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"registratiedatumTotEnMet": "2024-09-24T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertItemInResults(
                    data["results"], "uuid", str(publication.uuid), 1
                )

        with self.subTest("date is not exact"):
            with self.subTest("filter on lte date is exact match"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"registratiedatumTotEnMet": "2024-09-25T12:00:00-00:00"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 2)
                self.assertItemInResults(
                    data["results"], "uuid", str(publication.uuid), 1
                )
                self.assertItemInResults(
                    data["results"], "uuid", str(publication2.uuid), 1
                )

        with self.subTest(
            "filter both lt and gte to find publication between two dates"
        ):
            response = self.client.get(
                reverse("api:publication-list"),
                {
                    "registratiedatumVanaf": "2024-09-25T00:00:00-00:00",
                    "registratiedatumTot": "2024-09-26T00:00:00-00:00",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication2.uuid))

        with self.subTest(
            "filter both lte and gte to find publication between two dates"
        ):
            response = self.client.get(
                reverse("api:publication-list"),
                {
                    "registratiedatumVanaf": "2024-09-25T12:00:00-00:00",
                    "registratiedatumTotEnMet": "2024-09-25T12:00:00-00:00",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(publication2.uuid), 1)

    def test_list_publications_filter_search(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="Een prachtige titel met een heleboel woorden.",
            verkorte_titel="prachtige titel.",
        )
        publication2 = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="Een titel die anders is als de verkorte titel.",
            verkorte_titel="waarom is deze titel anders.",
        )

        with self.subTest("officele titel exacte match"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"search": "Een prachtige titel met een heleboel woorden."},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication.uuid))

        with self.subTest("verkorte titel exacte match"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"search": "waarom is deze titel anders."},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication2.uuid))

        with self.subTest("officele titel partial match"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"search": "prachtige titel met"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication.uuid))

        with self.subTest("verkorte titel partial match"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"search": "deze titel anders"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication2.uuid))

        with self.subTest("partial match both objects different fields"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"search": "titel."},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertEqual(data["results"][0]["uuid"], str(publication2.uuid))
            self.assertEqual(data["results"][1]["uuid"], str(publication.uuid))

    def test_list_publications_filter_owner(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
            # mimicking creating log though api
            audit_api_create(
                content_object=publication,
                user_id="123",
                user_display="buurman",
                object_data=serialize_instance(publication),
                remarks="test",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = PublicationFactory.create(
                informatie_categorieen=[ic2],
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
            # mimicking creating log though api
            audit_api_create(
                content_object=publication2,
                user_id="456",
                user_display="buurman",
                object_data=serialize_instance(publication2),
                remarks="test",
            )

        expected_first_item_data = {
            "uuid": str(publication.uuid),
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [],
            "publisher": str(publication.publisher.uuid),
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {"weergaveNaam": "buurman", "identifier": "123"},
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }
        expected_second_item_data = {
            "uuid": str(publication2.uuid),
            "informatieCategorieen": [str(ic2.uuid)],
            "diWooInformatieCategorieen": [str(ic2.uuid)],
            "onderwerpen": [],
            "publisher": str(publication2.publisher.uuid),
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title two",
            "verkorteTitel": "two",
            "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {"weergaveNaam": "buurman", "identifier": "456"},
            "registratiedatum": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }

        with (
            self.subTest("filter with existing eigenaar"),
            freeze_time("2024-10-01T00:00:00-00:00"),
        ):
            response = self.client.get(
                reverse("api:publication-list"),
                {"eigenaar": "123"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0], expected_first_item_data)

        with self.subTest("filter with none existing eigenaar"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"eigenaar": "39834594397543"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 0)

        with (
            self.subTest("filter with no input"),
            freeze_time("2024-10-01T00:00:00-00:00"),
        ):
            response = self.client.get(
                reverse("api:publication-list"),
                {"eigenaar": ""},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)

            self.assertEqual(data["results"][0], expected_second_item_data)
            self.assertEqual(data["results"][1], expected_first_item_data)

    def test_list_publication_filter_publication_status(self):
        published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked
        )
        list_url = reverse("api:publication-list")

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
                    "publicatiestatus": f"{PublicationStatusOptions.published},{PublicationStatusOptions.revoked}"
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(published.uuid))
            self.assertItemInResults(data["results"], "uuid", str(revoked.uuid))

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_detail_publication(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        topic = TopicFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            onderwerpen=[topic],
            publicatiestatus=PublicationStatusOptions.concept,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            archiefnominatie=ArchiveNominationChoices.retain,
            archiefactiedatum="2025-01-01",
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_first_item_data = {
            "uuid": str(publication.uuid),
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [str(topic.uuid)],
            "publisher": str(publication.publisher.uuid),
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.concept,
            "eigenaar": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }

        self.assertEqual(data, expected_first_item_data)

    def test_diwoo_informatie_categories(self):
        custom_ic, custom_ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.custom_entry
        )
        value_list_ic, value_list_ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )

        with self.subTest(
            "publication with only custom ics returns uuid of insappings verplicht ic"
        ):
            publication = PublicationFactory.create(
                informatie_categorieen=[custom_ic, custom_ic2]
            )
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(publication.uuid)},
            )

            response = self.client.get(detail_url, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json()["diWooInformatieCategorieen"],
                [str(self.inspannings_verplichting.uuid)],
            )

        with self.subTest("publication with ic from ic don't get transformed"):
            publication = PublicationFactory.create(
                informatie_categorieen=[value_list_ic, value_list_ic2]
            )
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(publication.uuid)},
            )

            response = self.client.get(detail_url, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertIn(str(value_list_ic.uuid), data["diWooInformatieCategorieen"])
            self.assertIn(str(value_list_ic2.uuid), data["diWooInformatieCategorieen"])

        with self.subTest(
            "publication with custom ic and inspannings verplicht ic dont have duplicate insappings verplicht ic uuid"
        ):
            publication = PublicationFactory.create(
                informatie_categorieen=[
                    custom_ic,
                    custom_ic2,
                    self.inspannings_verplichting,
                ]
            )
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(publication.uuid)},
            )

            response = self.client.get(detail_url, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json()["diWooInformatieCategorieen"],
                [str(self.inspannings_verplichting.uuid)],
            )

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_create_publication(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )
        topic = TopicFactory.create()
        organisation, organisation2, organisation3 = OrganisationFactory.create_batch(
            3, is_actief=True
        )
        deactivated_organisation = OrganisationFactory.create(is_actief=False)
        url = reverse("api:publication-list")

        with self.subTest("no information categories results in error"):
            data = {
                "officieleTitel": "bla",
                "verkorteTitel": "bla",
                "omschrijving": "bla",
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_data = response.json()
            self.assertEqual(
                response_data["informatieCategorieen"], [_("This field is required.")]
            )

        with self.subTest("deactivated organisation cannot be used as an organisation"):
            data = {
                "publisher": str(deactivated_organisation.uuid),
                "verantwoordelijke": str(deactivated_organisation.uuid),
                "opsteller": str(deactivated_organisation.uuid),
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_data = response.json()

            # format the same way drf does for gettext to translate the error message properly
            self.assertEqual(
                response_data["publisher"],
                [
                    _("Object with {slug_name}={value} does not exist.").format(
                        slug_name="uuid", value=deactivated_organisation.uuid
                    )
                ],
            )
            self.assertEqual(
                response_data["verantwoordelijke"],
                [
                    _("Object with {slug_name}={value} does not exist.").format(
                        slug_name="uuid", value=deactivated_organisation.uuid
                    )
                ],
            )
            self.assertNotIn(
                "opsteller",
                response_data,
            )

        with self.subTest("no publisher results in error"):
            data = {
                "informatieCategorieen": [str(ic.uuid)],
                "officieleTitel": "bla",
                "verkorteTitel": "bla",
                "omschrijving": "bla",
            }
            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_data = response.json()

            self.assertEqual(response_data["publisher"], [_("This field is required.")])

        with self.subTest("trying to create a revoked publication results in errors"):
            data = {
                "informatieCategorieen": [str(ic.uuid)],
                "publisher": str(organisation.uuid),
                "publicatiestatus": PublicationStatusOptions.revoked,
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_data = response.json()

            self.assertEqual(
                response_data["publicatiestatus"],
                [
                    _("You cannot create a {revoked} publication.").format(
                        revoked=PublicationStatusOptions.revoked.label.lower()
                    )
                ],
            )

        with self.subTest("complete data"):
            data = {
                "informatieCategorieen": [str(ic.uuid), str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "bronBewaartermijn": "Selectielijst gemeenten 2020",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2025-01-01",
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            response_data = response.json()
            expected_data = {
                "uuid": response_data[
                    "uuid"
                ],  # uuid gets generated so we are just testing that its there
                "informatieCategorieen": [str(ic.uuid), str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.concept,
                "eigenaar": {"weergaveNaam": "username", "identifier": "id"},
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "bronBewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2025-01-01",
                "toelichtingBewaartermijn": "",
            }

            # diWooInformatieCategorieen ordering is done on the UUID field to make sure there are no duplicated data.
            # Which results in unpredictable ordering for testing, so I test these individually
            self.assertIn(str(ic.uuid), response_data["diWooInformatieCategorieen"])
            self.assertIn(str(ic2.uuid), response_data["diWooInformatieCategorieen"])
            del response_data["diWooInformatieCategorieen"]
            self.assertEqual(response_data, expected_data)

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_update_publication(self):
        topic = TopicFactory.create()
        ic, ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )
        organisation, organisation2, organisation3 = OrganisationFactory.create_batch(
            3, is_actief=True
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic, ic2],
            publisher=organisation3,
            publicatiestatus=PublicationStatusOptions.concept,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            archiefactiedatum="2035-01-01",
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with self.subTest("empty information categories results in error"):
            data = {
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
            }

            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_data = response.json()
            self.assertEqual(
                response_data["informatieCategorieen"], [_("This field is required.")]
            )

        with self.subTest("complete data"):
            data = {
                "informatieCategorieen": [str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "publicatiestatus": PublicationStatusOptions.published,
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
                "bronBewaartermijn": "changed",
                "selectiecategorie": "changed",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "archiefactiedatum": "2025-01-01",
                "toelichtingBewaartermijn": "changed",
            }

            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()
            expected_data = {
                "uuid": response_data[
                    "uuid"
                ],  # uuid gets generated so we are just testing that its there
                "informatieCategorieen": [str(ic2.uuid)],
                "diWooInformatieCategorieen": [str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "publicatiestatus": PublicationStatusOptions.published,
                "omschrijving": "changed description",
                "eigenaar": None,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "bronBewaartermijn": "changed",
                "selectiecategorie": "changed",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "archiefactiedatum": "2025-01-01",
                "toelichtingBewaartermijn": "changed",
            }

            self.assertEqual(response_data, expected_data)

    def test_update_publication_onderwerpen_field(self):
        topic = TopicFactory.create()
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            onderwerpen=[topic],
            publisher=organisation,
            publicatiestatus=PublicationStatusOptions.concept,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with self.subTest("update without onderwerpen doesn't alter the value"):
            data = {
                "informatieCategorieen": [str(ic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation.uuid),
                "opsteller": str(organisation.uuid),
                "publicatiestatus": PublicationStatusOptions.published,
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
            }

            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["onderwerpen"], [str(topic.uuid)])
            self.assertTrue(publication.onderwerpen.filter(uuid=topic.uuid).exists())

        with self.subTest("update onderwerpen with empty list"):
            data = {
                "informatieCategorieen": [str(ic.uuid)],
                "onderwerpen": [],  # relevant field
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation.uuid),
                "opsteller": str(organisation.uuid),
                "publicatiestatus": PublicationStatusOptions.published,
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
            }

            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["onderwerpen"], [])
            self.assertFalse(publication.onderwerpen.filter(uuid=topic.uuid).exists())

    def test_update_revoked_publication_cannot_be_modified(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.revoked,
            publisher=organisation,
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publisher": str(organisation.uuid),
            "publicatiestatus": PublicationStatusOptions.published,
            "officieleTitel": "changed offical title",
            "verkorteTitel": "changed short title",
            "omschrijving": "changed description",
        }

        response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = response.json()
        self.assertEqual(
            response_data["publicatiestatus"],
            [
                _("You cannot modify a {revoked} publication.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                )
            ],
        )

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_partial_update_publication(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        topic = TopicFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            onderwerpen=[topic],
            publisher=organisation,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )
        data = {
            "officieleTitel": "changed offical title",
        }

        response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        expected_data = {
            "uuid": response_data[
                "uuid"
            ],  # uuid gets generated so we are just testing that its there
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [str(topic.uuid)],
            "publisher": str(organisation.uuid),
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "changed offical title",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "bronBewaartermijn": publication.bron_bewaartermijn,
            "selectiecategorie": "",
            "archiefnominatie": "",
            "archiefactiedatum": str(publication.archiefactiedatum),
            "toelichtingBewaartermijn": "",
        }

        # test that only officiele_titel got changed
        self.assertEqual(response_data, expected_data)

    def test_partial_update_when_revoking_publication_the_published_documents_also_get_revoked(
        self,
    ):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.published,
        )
        published_document = DocumentFactory.create(
            publicatie=publication, publicatiestatus=PublicationStatusOptions.published
        )
        concept_document = DocumentFactory.create(
            publicatie=publication, publicatiestatus=PublicationStatusOptions.concept
        )
        revoked_document = DocumentFactory.create(
            publicatie=publication, publicatiestatus=PublicationStatusOptions.revoked
        )

        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )
        data = {"publicatiestatus": PublicationStatusOptions.revoked}

        response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        published_document.refresh_from_db()
        concept_document.refresh_from_db()
        revoked_document.refresh_from_db()

        self.assertEqual(
            response.json()["publicatiestatus"], PublicationStatusOptions.revoked
        )
        self.assertEqual(
            published_document.publicatiestatus, PublicationStatusOptions.revoked
        )
        self.assertEqual(
            concept_document.publicatiestatus, PublicationStatusOptions.concept
        )
        self.assertEqual(
            revoked_document.publicatiestatus, PublicationStatusOptions.revoked
        )

    def test_destroy_publication(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        response = self.client.delete(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Publication.objects.filter(uuid=publication.uuid).exists())

    @patch("woo_publications.publications.api.viewsets.index_publication.delay")
    def test_publish_publication_update_schedules_index_task(
        self, mock_index_publication_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                detail_url,
                data={"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
        latest_publication = Publication.objects.order_by("-pk").first()
        assert latest_publication is not None
        mock_index_publication_delay.assert_called_once_with(
            publication_id=latest_publication.pk
        )

    @patch("woo_publications.publications.api.viewsets.index_publication.delay")
    def test_publish_publication_create_schedules_index_task(
        self, mock_index_publication_delay: MagicMock
    ):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        organisation = OrganisationFactory.create(is_actief=True)
        list_url = reverse("api:publication-list")

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publicatiestatus": PublicationStatusOptions.concept,
            "publisher": str(organisation.uuid),
            "verantwoordelijke": str(organisation.uuid),
            "opsteller": str(organisation.uuid),
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                list_url,
                data=data,
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        latest_publication = Publication.objects.order_by("-pk").first()
        assert latest_publication is not None
        mock_index_publication_delay.assert_called_once_with(
            publication_id=latest_publication.pk
        )

    @patch(
        "woo_publications.publications.api.viewsets.remove_publication_from_index.delay"
    )
    def test_revoke_publication_schedules_index_removal_task(
        self, mock_remove_publication_from_index_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                detail_url,
                data={"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
        latest_publication = Publication.objects.order_by("-pk").first()
        assert latest_publication is not None
        mock_remove_publication_from_index_delay.assert_called_once_with(
            publication_id=latest_publication.pk
        )

    @patch(
        "woo_publications.publications.api.viewsets.remove_publication_from_index.delay"
    )
    def test_concept_publication_schedules_index_removal_task(
        self, mock_remove_publication_from_index_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                detail_url,
                data={"publicatiestatus": PublicationStatusOptions.concept},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
        latest_publication = Publication.objects.order_by("-pk").first()
        assert latest_publication is not None
        mock_remove_publication_from_index_delay.assert_called_once_with(
            publication_id=latest_publication.pk
        )
