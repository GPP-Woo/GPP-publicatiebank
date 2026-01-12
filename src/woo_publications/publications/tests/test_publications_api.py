import tempfile
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.models import OrganisationMember, OrganisationUnit
from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    OrganisationUnitFactory,
    UserFactory,
)
from woo_publications.api.tests.mixins import (
    APIKeyUnAuthorizedMixin,
    APITestCaseMixin,
    TokenAuthMixin,
)
from woo_publications.config.models import GlobalConfiguration
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.constants import InformationCategoryOrigins
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from ..models import Publication, PublicationIdentifier
from .factories import (
    DocumentFactory,
    PublicationFactory,
    PublicationIdentifierFactory,
    TopicFactory,
)

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PublicationApiTestsCase(TokenAuthMixin, APITestCaseMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # diWooInformatieCategorieen needs to have inspannings verplichting record in
        # case of custom entries
        cls.inspannings_verplichting = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list,
            identifier=settings.INSPANNINGSVERPLICHTING_IDENTIFIER,
        )
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=AUDIT_HEADERS["AUDIT_USER_ID"],
            naam=AUDIT_HEADERS["AUDIT_USER_REPRESENTATION"],
        )

        # the get_inspannings_verplichting func which is called while fetching the
        # diWooInformatieCategorieen data is cached.
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
                eigenaar=self.organisation_member,
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
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.concept,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
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
                "urlPublicatieIntern": "",
                "urlPublicatieExtern": "",
                "informatieCategorieen": [str(ic.uuid)],
                "diWooInformatieCategorieen": [str(ic.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(publication.publisher.uuid),
                "kenmerken": [],
                "verantwoordelijke": None,
                "opsteller": None,
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur "
                "adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.published,
                "eigenaar": {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
                "eigenaarGroep": None,
                "registratiedatum": "2024-09-25T14:30:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
                "datumBeginGeldigheid": None,
                "datumEindeGeldigheid": None,
                "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
                "ingetrokkenOp": None,
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
                "urlPublicatieIntern": "",
                "urlPublicatieExtern": "",
                "informatieCategorieen": [str(ic2.uuid)],
                "diWooInformatieCategorieen": [str(ic2.uuid)],
                "onderwerpen": [],
                "publisher": str(publication2.publisher.uuid),
                "kenmerken": [],
                "verantwoordelijke": None,
                "opsteller": None,
                "officieleTitel": "title two",
                "verkorteTitel": "two",
                "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                "publicatiestatus": PublicationStatusOptions.concept,
                "eigenaar": {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
                "eigenaarGroep": None,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "datumBeginGeldigheid": None,
                "datumEindeGeldigheid": None,
                "gepubliceerdOp": None,
                "ingetrokkenOp": None,
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
                eigenaar=self.organisation_member,
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
                eigenaar=self.organisation_member,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        expected_first_item_data = {
            "uuid": str(publication.uuid),
            "urlPublicatieIntern": "",
            "urlPublicatieExtern": "",
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [],
            "publisher": str(publication.publisher.uuid),
            "kenmerken": [],
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {
                "identifier": self.organisation_member.identifier,
                "weergaveNaam": self.organisation_member.naam,
            },
            "eigenaarGroep": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "gepubliceerdOp": "2024-09-24T14:00:00+02:00",
            "ingetrokkenOp": None,
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }
        expected_second_item_data = {
            "uuid": str(publication2.uuid),
            "urlPublicatieIntern": "",
            "urlPublicatieExtern": "",
            "informatieCategorieen": [str(ic2.uuid)],
            "diWooInformatieCategorieen": [str(ic2.uuid)],
            "onderwerpen": [],
            "publisher": str(publication2.publisher.uuid),
            "kenmerken": [],
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title two",
            "verkorteTitel": "two",
            "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, "
            "facilisis mollis urna.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {
                "identifier": self.organisation_member.identifier,
                "weergaveNaam": self.organisation_member.naam,
            },
            "eigenaarGroep": None,
            "registratiedatum": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
            "ingetrokkenOp": None,
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

        with self.subTest("filter on lte date is exact match"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"registratiedatumTotEnMet": "2024-09-25T12:00:00-00:00"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(publication.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(publication2.uuid), 1)

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

    def test_list_publications_filter_archiefactiedatum(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic], archiefactiedatum="2024-09-23"
        )
        publication2 = PublicationFactory.create(
            informatie_categorieen=[ic], archiefactiedatum="2024-09-25"
        )
        publication3 = PublicationFactory.create(
            informatie_categorieen=[ic], archiefactiedatum="2024-09-27"
        )

        with self.subTest("gte specific tests"):
            with self.subTest("filter on gte date is exact match"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"archiefactiedatumVanaf": "2024-09-27"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertEqual(data["results"][0]["uuid"], str(publication3.uuid))

            with self.subTest("filter on gte date is greater then publication"):
                response = self.client.get(
                    reverse("api:publication-list"),
                    {"archiefactiedatumVanaf": "2024-09-26"},
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
                    {"archiefactiedatumTot": "2024-09-24"},
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
                    {"archiefactiedatumTotEnMet": "2024-09-23"},
                    headers=AUDIT_HEADERS,
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()

                self.assertEqual(data["count"], 1)
                self.assertItemInResults(
                    data["results"], "uuid", str(publication.uuid), 1
                )

        with self.subTest("filter on lte date is exact match"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"archiefactiedatumTotEnMet": "2024-09-25"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(publication.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(publication2.uuid), 1)

        with self.subTest(
            "filter both lt and gte to find publication between two dates"
        ):
            response = self.client.get(
                reverse("api:publication-list"),
                {
                    "archiefactiedatumVanaf": "2024-09-24",
                    "archiefactiedatumTot": "2024-09-26",
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication2.uuid))

        with self.subTest(
            "filter both lte and gte on exact date to find "
            "publication 'between' two dates"
        ):
            response = self.client.get(
                reverse("api:publication-list"),
                {
                    "archiefactiedatumVanaf": "2024-09-25",
                    "archiefactiedatumTotEnMet": "2024-09-25",
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

    def test_list_publication_filter_archiefnominatie(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            archiefnominatie=ArchiveNominationChoices.retain,
        )
        PublicationFactory.create(
            informatie_categorieen=[ic],
            archiefnominatie=ArchiveNominationChoices.destroy,
        )

        response = self.client.get(
            reverse("api:publication-list"),
            {"archiefnominatie": ArchiveNominationChoices.retain},
            headers=AUDIT_HEADERS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["uuid"], str(publication.uuid))

    def test_list_publications_filter_owner(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2, oorsprong=InformationCategoryOrigins.value_list
        )
        org_member_1 = OrganisationMemberFactory.create(
            identifier="123", naam="buurman"
        )
        org_member_2 = OrganisationMemberFactory.create(
            identifier="456", naam="buurman"
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic],
                eigenaar=org_member_1,
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
                eigenaar=org_member_2,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )

        expected_first_item_data = {
            "uuid": str(publication.uuid),
            "urlPublicatieIntern": "",
            "urlPublicatieExtern": "",
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [],
            "publisher": str(publication.publisher.uuid),
            "kenmerken": [],
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {"weergaveNaam": "buurman", "identifier": "123"},
            "eigenaarGroep": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "gepubliceerdOp": "2024-09-24T14:00:00+02:00",
            "ingetrokkenOp": None,
            "toelichtingBewaartermijn": "",
        }
        expected_second_item_data = {
            "uuid": str(publication2.uuid),
            "urlPublicatieIntern": "",
            "urlPublicatieExtern": "",
            "informatieCategorieen": [str(ic2.uuid)],
            "diWooInformatieCategorieen": [str(ic2.uuid)],
            "onderwerpen": [],
            "publisher": str(publication2.publisher.uuid),
            "kenmerken": [],
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title two",
            "verkorteTitel": "two",
            "omschrijving": "Vestibulum eros nulla, tincidunt sed est non, "
            "facilisis mollis urna.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {"weergaveNaam": "buurman", "identifier": "456"},
            "eigenaarGroep": None,
            "registratiedatum": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
            "ingetrokkenOp": None,
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

    def test_list_publications_filter_owner_group(self):
        org_unit_1 = OrganisationUnitFactory.create(identifier="123", naam="duplicate")
        org_unit_2 = OrganisationUnitFactory.create(identifier="456", naam="duplicate")

        PublicationFactory.create()
        PublicationFactory.create(eigenaar_groep=org_unit_1)
        publication_with_owner_group_2 = PublicationFactory.create(
            eigenaar_groep=org_unit_2
        )

        with self.subTest("filter with existing owner group"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"eigenaarGroep": "456"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(
                data["results"][0]["uuid"], str(publication_with_owner_group_2.uuid)
            )

        with self.subTest("filter with non-existent owner group"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"eigenaarGroep": "999"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 0)

        with self.subTest("filter with non input"):
            response = self.client.get(
                reverse("api:publication-list"),
                {"eigenaarGroep": ""},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 3)

    def test_list_publications_filter_owner_OR_owner_group(self):
        org_member = OrganisationMemberFactory.create(identifier="123")
        org_unit = OrganisationUnitFactory.create(identifier="456")
        PublicationFactory.create(
            eigenaar=org_member,
            eigenaar_groep=None,
        )
        PublicationFactory.create(
            eigenaar__identifier="something-else",
            eigenaar_groep=org_unit,
        )

        response = self.client.get(
            reverse("api:publication-list"),
            {"eigenaarGroep": "456", "eigenaar": "123"},
            headers=AUDIT_HEADERS,
        )

        # we expect these filter parameters to be OR-ed together rather than AND,
        # which results in both publications being returned/matched
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_list_publication_filter_publication_status(self):
        published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        revoked = PublicationFactory.create(revoked=True)
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

    def test_list_publication_filter_kenmerken(self):
        publication_1, publication_2 = PublicationFactory.create_batch(
            2, publicatiestatus=PublicationStatusOptions.published
        )
        PublicationIdentifierFactory(
            publicatie=publication_1, kenmerk="kenmerk-1", bron="bron-1"
        )
        list_url = reverse("api:publication-list")

        with self.subTest("filter on none existing kenmerk"):
            response = self.client.get(
                list_url,
                {"kenmerk": "does not exist"},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)

        with self.subTest("filter on existing kenmerk"):
            response = self.client.get(
                list_url,
                {"kenmerk": "kenmerk-1"},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication_1.uuid))

        with self.subTest("filter on none existing bron"):
            response = self.client.get(
                list_url,
                {"bron": "does not exist"},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 0)

        with self.subTest("filter on existing bron"):
            response = self.client.get(
                list_url,
                {"bron": "bron-1"},
                headers=AUDIT_HEADERS,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(publication_1.uuid))

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_detail_publication(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        topic = TopicFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            onderwerpen=[topic],
            eigenaar=self.organisation_member,
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
            "urlPublicatieIntern": "",
            "urlPublicatieExtern": "",
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [str(topic.uuid)],
            "publisher": str(publication.publisher.uuid),
            "kenmerken": [],
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.concept,
            "eigenaar": {
                "identifier": self.organisation_member.identifier,
                "weergaveNaam": self.organisation_member.naam,
            },
            "eigenaarGroep": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "gepubliceerdOp": None,
            "ingetrokkenOp": None,
            "bronBewaartermijn": "Selectielijst gemeenten 2020",
            "selectiecategorie": "",
            "archiefnominatie": ArchiveNominationChoices.retain,
            "archiefactiedatum": "2025-01-01",
            "toelichtingBewaartermijn": "",
        }

        self.assertEqual(data, expected_first_item_data)

    def test_publication_internal_url(self):
        global_configuration = GlobalConfiguration.get_solo()
        self.addCleanup(GlobalConfiguration.clear_cache)
        global_configuration.gpp_app_publication_url_template = (
            "https://woo-app.example.com/<UUID>"
        )
        global_configuration.save()
        publication = PublicationFactory.create(
            uuid="771b79e5-3ba7-4fdf-9a89-00a6a5227a8d"
        )

        with self.subTest("detail endpoint"):
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication.uuid}
            )

            response = self.client.get(endpoint, headers=AUDIT_HEADERS)

            self.assertEqual(
                response.json()["urlPublicatieIntern"],
                "https://woo-app.example.com/771b79e5-3ba7-4fdf-9a89-00a6a5227a8d",
            )

        with self.subTest("list endpoint"):
            endpoint = reverse("api:publication-list")

            response = self.client.get(endpoint, headers=AUDIT_HEADERS)

            result = response.json()["results"][0]
            self.assertEqual(
                result["urlPublicatieIntern"],
                "https://woo-app.example.com/771b79e5-3ba7-4fdf-9a89-00a6a5227a8d",
            )

    def test_publication_external_url(self):
        global_configuration = GlobalConfiguration.get_solo()
        self.addCleanup(GlobalConfiguration.clear_cache)
        global_configuration.gpp_burgerportaal_publication_url_template = (
            "https://woo-burgerportaal.example.com/<UUID>"
        )
        global_configuration.save()
        publication = PublicationFactory.create(
            uuid="771b79e5-3ba7-4fdf-9a89-00a6a5227a8d"
        )

        with self.subTest("detail endpoint"):
            endpoint = reverse(
                "api:publication-detail", kwargs={"uuid": publication.uuid}
            )

            response = self.client.get(endpoint, headers=AUDIT_HEADERS)

            self.assertEqual(
                response.json()["urlPublicatieExtern"],
                "https://woo-burgerportaal.example.com/771b79e5-3ba7-4fdf-9a89-00a6a5227a8d",
            )

        with self.subTest("list endpoint"):
            endpoint = reverse("api:publication-list")

            response = self.client.get(endpoint, headers=AUDIT_HEADERS)

            result = response.json()["results"][0]
            self.assertEqual(
                result["urlPublicatieExtern"],
                "https://woo-burgerportaal.example.com/771b79e5-3ba7-4fdf-9a89-00a6a5227a8d",
            )

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
            "publication with custom ic and inspannings verplicht ic dont have "
            "duplicate insappings verplicht ic uuid"
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
            2,
            oorsprong=InformationCategoryOrigins.value_list,
            bron_bewaartermijn="bewaartermijn",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
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

            # format the same way drf does for gettext to translate the error
            # message properly
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

        with self.subTest("complete data"):
            data = {
                "informatieCategorieen": [str(ic.uuid), str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "kenmerken": [
                    {"kenmerk": "kenmerk 1", "bron": "bron 1"},
                    {"kenmerk": "kenmerk 2", "bron": "bron 2"},
                ],
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.",
                "datumBeginGeldigheid": "2025-06-19",
                "datumEindeGeldigheid": "2025-06-19",
                # These values will not be overwritten because the status is concept
                "bronBewaartermijn": "THIS VALUE WILL BE USED",
                "selectiecategorie": "THIS VALUE WILL BE USED",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "archiefactiedatum": "3000-01-01",
                "toelichtingBewaartermijn": "THIS VALUE WILL BE USED",
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            response_data = response.json()
            expected_data = {
                "uuid": response_data[
                    "uuid"
                ],  # uuid gets generated so we are just testing that its there
                "urlPublicatieIntern": "",
                "urlPublicatieExtern": "",
                "informatieCategorieen": [str(ic.uuid), str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "kenmerken": [
                    {"kenmerk": "kenmerk 1", "bron": "bron 1"},
                    {"kenmerk": "kenmerk 2", "bron": "bron 2"},
                ],
                "officieleTitel": "title one",
                "verkorteTitel": "one",
                "omschrijving": "Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.concept,
                "eigenaar": {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
                "eigenaarGroep": None,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "datumBeginGeldigheid": "2025-06-19",
                "datumEindeGeldigheid": "2025-06-19",
                "gepubliceerdOp": None,
                "ingetrokkenOp": None,
                "bronBewaartermijn": "THIS VALUE WILL BE USED",
                "selectiecategorie": "THIS VALUE WILL BE USED",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "archiefactiedatum": "3000-01-01",
                "toelichtingBewaartermijn": "THIS VALUE WILL BE USED",
            }

            # diWooInformatieCategorieen ordering is done on the UUID field to make
            # sure there are no duplicated data, which results in unpredictable ordering
            # for testing, so I test these individually
            self.assertIn(str(ic.uuid), response_data["diWooInformatieCategorieen"])
            self.assertIn(str(ic2.uuid), response_data["diWooInformatieCategorieen"])
            del response_data["diWooInformatieCategorieen"]
            self.assertEqual(response_data, expected_data)

            created_publication = Publication.objects.get(uuid=response_data["uuid"])
            self.assertTrue(
                PublicationIdentifier.objects.filter(
                    publicatie=created_publication, kenmerk="kenmerk 1", bron="bron 1"
                ).exists()
            )
            self.assertTrue(
                PublicationIdentifier.objects.filter(
                    publicatie=created_publication, kenmerk="kenmerk 2", bron="bron 2"
                ).exists()
            )

        with self.subTest("with custom eigenaar given"):
            self.assertFalse(
                OrganisationMember.objects.filter(
                    identifier="test-identifier",
                    naam="test-naam",
                ).exists()
            )

            data = {
                "informatieCategorieen": [str(ic.uuid)],
                "publisher": str(organisation.uuid),
                "publicatiestatus": PublicationStatusOptions.published,
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
                "eigenaar": {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

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
                    identifier="test-identifier",
                    naam="test-naam",
                ).exists()
            )

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_update_publication(self):
        topic = TopicFactory.create()
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            oorsprong=InformationCategoryOrigins.value_list,
            bron_bewaartermijn="changed",
            selectiecategorie="changed",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=1,
            toelichting_bewaartermijn="changed",
        )
        organisation, organisation2, organisation3 = OrganisationFactory.create_batch(
            3, is_actief=True
        )
        OrganisationMemberFactory.create(
            identifier="test-identifier",
            naam="test-naam",
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic, ic2],
            publisher=organisation3,
            eigenaar=self.organisation_member,
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            archiefactiedatum="2035-01-01",
        )
        publication_identifier = PublicationIdentifierFactory.create(
            publicatie=publication, kenmerk="kenmerk 1", bron="bron 1"
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
                "datumBeginGeldigheid": "2025-06-19",
                "datumEindeGeldigheid": "2025-06-19",
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "omschrijving": "changed description",
                "eigenaar": {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
                # retention fields will be overwritten by the altering of the ic's
                "bronBewaartermijn": "IGNORED",
                "selectiecategorie": "IGNORED",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "3000-01-01",
                "toelichtingBewaartermijn": "IGNORED",
            }

            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()
            expected_data = {
                "uuid": response_data[
                    "uuid"
                ],  # uuid gets generated so we are just testing that its there
                "urlPublicatieIntern": "",
                "urlPublicatieExtern": "",
                "informatieCategorieen": [str(ic2.uuid)],
                "diWooInformatieCategorieen": [str(ic2.uuid)],
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation2.uuid),
                "opsteller": str(organisation3.uuid),
                "kenmerken": [
                    # when the field isn't given in the update
                    # expect the data to not be changed
                    {"kenmerk": "kenmerk 1", "bron": "bron 1"}
                ],
                "officieleTitel": "changed offical title",
                "verkorteTitel": "changed short title",
                "publicatiestatus": PublicationStatusOptions.published,
                "omschrijving": "changed description",
                "eigenaar": {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
                "eigenaarGroep": None,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
                "datumBeginGeldigheid": "2025-06-19",
                "datumEindeGeldigheid": "2025-06-19",
                "gepubliceerdOp": "2024-09-24T14:00:00+02:00",
                "ingetrokkenOp": None,
                "bronBewaartermijn": "changed",
                "selectiecategorie": "changed",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "archiefactiedatum": "2025-09-24",
                "toelichtingBewaartermijn": "changed",
            }

            self.assertEqual(response_data, expected_data)
            # no new organisation member got created
            self.assertEqual(
                OrganisationMember.objects.filter(
                    identifier="test-identifier",
                    naam="test-naam",
                ).count(),
                1,
            )
            self.assertTrue(
                PublicationIdentifier.objects.filter(
                    pk=publication_identifier.pk
                ).exists()
            )

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
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            revoked=True,
            publisher=organisation,
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publisher": str(organisation.uuid),
            "publicatiestatus": PublicationStatusOptions.revoked,
            "officieleTitel": "changed offical title",
            "verkorteTitel": "changed short title",
            "omschrijving": "changed description",
        }

        response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["non_field_errors"],
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
            eigenaar=self.organisation_member,
            onderwerpen=[topic],
            publisher=organisation,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            archiefactiedatum="2034-09-24",
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
            "urlPublicatieIntern": "",
            "urlPublicatieExtern": "",
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [str(topic.uuid)],
            "publisher": str(organisation.uuid),
            "kenmerken": [],
            "verantwoordelijke": None,
            "opsteller": None,
            "officieleTitel": "changed offical title",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "publicatiestatus": PublicationStatusOptions.published,
            "eigenaar": {
                "identifier": self.organisation_member.identifier,
                "weergaveNaam": self.organisation_member.naam,
            },
            "eigenaarGroep": None,
            "registratiedatum": "2024-09-24T14:00:00+02:00",
            "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "gepubliceerdOp": "2024-09-24T14:00:00+02:00",
            "ingetrokkenOp": None,
            "bronBewaartermijn": publication.bron_bewaartermijn,
            "selectiecategorie": "",
            "archiefnominatie": "",
            "archiefactiedatum": "2034-09-24",
            "toelichtingBewaartermijn": "",
        }

        # test that only officiele_titel got changed
        self.assertEqual(response_data, expected_data)

    def test_partial_publication_kenmerken(self):
        publication = PublicationFactory.create()
        PublicationIdentifierFactory.create(
            publicatie=publication, kenmerk="kenmerk 1", bron="bron 1"
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
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
                PublicationIdentifier.objects.filter(
                    publicatie=publication, kenmerk="kenmerk 1", bron="bron 1"
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
                PublicationIdentifier.objects.filter(
                    publicatie=publication, kenmerk="kenmerk 1", bron="bron 1"
                ).exists()
            )
            self.assertTrue(
                PublicationIdentifier.objects.filter(
                    publicatie=publication, kenmerk="kenmerk 2", bron="bron 2"
                ).exists()
            )

        with self.subTest("updating kenmerken empty array"):
            data = {"kenmerken": []}

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()

            self.assertEqual(response_data["kenmerken"], [])
            self.assertFalse(
                PublicationIdentifier.objects.filter(
                    publicatie=publication, kenmerk="kenmerk 1", bron="bron 1"
                ).exists()
            )
            self.assertFalse(
                PublicationIdentifier.objects.filter(
                    publicatie=publication, kenmerk="kenmerk 2", bron="bron 2"
                ).exists()
            )

    def test_kenmerken_validation(self):
        publication = PublicationFactory.create()
        publication2 = PublicationFactory.create()
        PublicationIdentifierFactory.create(
            publicatie=publication, kenmerk="kenmerk 1", bron="bron 1"
        )
        PublicationIdentifierFactory.create(
            publicatie=publication, kenmerk="kenmerk 2", bron="bron 2"
        )
        with self.subTest("validate duplicated items given"):
            url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(publication.uuid)},
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
                "api:publication-detail",
                kwargs={"uuid": str(publication2.uuid)},
            )
            data = {
                "kenmerken": [
                    {"kenmerk": "kenmerk 1", "bron": "kenmerk 1"},
                ]
            }

            response = self.client.patch(url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_publication_new_owner(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            eigenaar=self.organisation_member,
        )

        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        self.assertFalse(
            OrganisationMember.objects.filter(
                identifier="test-identifier", naam="test-naam"
            )
        )

        with self.subTest("Incomplete owner data"):
            data = {
                "eigenaar": {
                    # No "identifier" field given
                    "weergaveNaam": "test-naam",
                },
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            response_data = response.json()
            self.assertEqual(
                response_data["eigenaar"],
                {
                    "nonFieldErrors": [
                        _(
                            "The fields 'naam' and 'weergaveNaam' have to be "
                            "both present or excluded."
                        )
                    ]
                },
            )

        with self.subTest("complete owner data"):
            data = {
                "eigenaar": {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()

            self.assertEqual(
                response_data["eigenaar"],
                {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            )
            # OrganisationMember got created
            self.assertTrue(
                OrganisationMember.objects.filter(
                    identifier="test-identifier", naam="test-naam"
                )
            )

    def test_set_owner_group_on_publication(self):
        ic = InformationCategoryFactory.create(
            oorsprong=InformationCategoryOrigins.value_list
        )
        publication = PublicationFactory.create(
            informatie_categorieen=[ic], eigenaar_groep=None
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )
        assert not OrganisationUnit.objects.exists()

        with self.subTest("incomplete owner group data"):
            data = {
                "eigenaarGroep": {
                    # No "identifier" field given
                    "weergaveNaam": "test-naam",
                },
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            response_data = response.json()
            self.assertEqual(
                response_data["eigenaarGroep"],
                {
                    "nonFieldErrors": [
                        _(
                            "The fields 'naam' and 'weergaveNaam' have to be "
                            "both present or excluded."
                        )
                    ]
                },
            )

        with self.subTest("create new organisation unit"):
            data = {
                "eigenaarGroep": {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response_data = response.json()

            self.assertEqual(
                response_data["eigenaarGroep"],
                {
                    "identifier": "test-identifier",
                    "weergaveNaam": "test-naam",
                },
            )
            # OrganisationMember got created
            self.assertTrue(
                OrganisationUnit.objects.filter(
                    identifier="test-identifier", naam="test-naam"
                ).exists()
            )

        with self.subTest("update existing organisation unit"):
            other_org_unit = OrganisationUnitFactory.create(
                identifier="other", naam="Other unit"
            )
            publication.eigenaar_groep = other_org_unit
            publication.save()

            data = {
                "eigenaarGroep": {
                    "identifier": "other",
                    "weergaveNaam": "updated name",
                },
            }

            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            publication.refresh_from_db()
            other_org_unit.refresh_from_db()
            self.assertEqual(publication.eigenaar_groep, other_org_unit)
            self.assertEqual(other_org_unit.identifier, "other")
            self.assertEqual(other_org_unit.naam, "updated name")

        with self.subTest("create publication"):
            assert not OrganisationUnit.objects.filter(
                identifier="from-create"
            ).exists()
            url = reverse("api:publication-list")
            data = {
                "publicatiestatus": PublicationStatusOptions.concept,
                "officieleTitel": "title one",
                "eigenaarGroep": {
                    "identifier": "from-create",
                    "weergaveNaam": "Created",
                },
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            org_unit = OrganisationUnit.objects.get(identifier="from-create")
            self.assertEqual(org_unit.naam, "Created")

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

    @patch("woo_publications.publications.tasks.index_publication.delay")
    def test_create_published_publication_schedules_index_task(
        self, mock_index_publication_delay: MagicMock
    ):
        information_category = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        list_url = reverse("api:publication-list")
        body = {
            "informatieCategorieen": [str(information_category.uuid)],
            "publisher": str(organisation.uuid),
            "verantwoordelijke": str(organisation.uuid),
            "opsteller": str(organisation.uuid),
            "officieleTitel": "Test",
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(list_url, data=body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_publication = Publication.objects.get()
        mock_index_publication_delay.assert_called_once_with(
            publication_id=created_publication.pk
        )

    @patch("woo_publications.publications.tasks.index_publication.delay")
    def test_updated_publication_schedules_index_task(
        self, mock_index_publication_delay: MagicMock
    ):
        """
        Assert that the search index update task is always triggered on update.

        Even without status changes, metadata updates must reach the search index.
        """
        information_category = InformationCategoryFactory.create()
        for _status in PublicationStatusOptions:
            mock_index_publication_delay.reset_mock()

            with self.subTest(status=_status):
                publication = PublicationFactory.create(
                    publicatiestatus=PublicationStatusOptions.concept,
                    informatie_categorieen=[information_category],
                )
                endpoint = reverse(
                    "api:publication-detail",
                    kwargs={"uuid": str(publication.uuid)},
                )
                body = self.client.get(endpoint, headers=AUDIT_HEADERS).json()

                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.put(endpoint, body, headers=AUDIT_HEADERS)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                mock_index_publication_delay.assert_called_once_with(
                    publication_id=publication.pk
                )

    @patch("woo_publications.publications.tasks.index_document.delay")
    def test_publication_update_publisher_or_ic_schedules_document_index_task(
        self, mock_index_document_delay: MagicMock
    ):
        ic_1, ic_2 = InformationCategoryFactory.create_batch(2)
        publisher_1, publisher_2 = OrganisationFactory.create_batch(2, is_actief=True)
        publication = PublicationFactory.create(
            informatie_categorieen=[ic_1],
            publisher=publisher_1,
            officiele_titel="title one",
        )
        document_1, document_2 = DocumentFactory.create_batch(2, publicatie=publication)
        endpoint = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with self.subTest(
            "update value other than publisher or ic doesn't trigger schedule"
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    endpoint, {"officieleTitel": "changed titel"}, headers=AUDIT_HEADERS
                )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_index_document_delay.assert_not_called()

        with self.subTest("update publisher triggers schedule"):
            mock_index_document_delay.reset_mock()

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    endpoint,
                    {"publisher": str(publisher_2.uuid)},
                    headers=AUDIT_HEADERS,
                )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_index_document_delay.assert_has_calls(
                [
                    call(document_id=document_1.pk),
                    call(document_id=document_2.pk),
                ],
                any_order=True,
            )

        with self.subTest("update information category triggers schedule"):
            mock_index_document_delay.reset_mock()

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    endpoint,
                    {"informatieCategorieen": [str(ic_2.uuid)]},
                    headers=AUDIT_HEADERS,
                )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_index_document_delay.assert_has_calls(
                [
                    call(document_id=document_1.pk),
                    call(document_id=document_2.pk),
                ],
                any_order=True,
            )

    @patch("woo_publications.publications.tasks.update_document_rsin.delay")
    def test_publication_update_publisher_schedules_document_rsin_update_task(
        self, mock_update_document_rsin_delay: MagicMock
    ):
        self.addCleanup(GlobalConfiguration.clear_cache)
        config = GlobalConfiguration.get_solo()
        config.organisation_rsin = "112345670"
        config.save()

        publisher = OrganisationFactory.create(rsin="000000000", is_actief=True)
        new_publisher_with_rsin = OrganisationFactory.create(
            rsin="123456782", is_actief=True
        )
        new_publisher_without_rsin = OrganisationFactory.create(rsin="", is_actief=True)
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept, publisher=publisher
        )
        published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published, publisher=publisher
        )
        concept_document = DocumentFactory.create(
            publicatie=concept,
            publicatiestatus=PublicationStatusOptions.concept,
            with_registered_document=True,
        )
        published_document = DocumentFactory.create(
            publicatie=published,
            publicatiestatus=PublicationStatusOptions.published,
            with_registered_document=True,
        )

        with self.subTest("update concept with new publisher rsin"):
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(concept.uuid)},
            )

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    detail_url,
                    {"publisher": str(new_publisher_with_rsin.uuid)},
                    headers=AUDIT_HEADERS,
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_update_document_rsin_delay.assert_called_with(
                document_id=concept_document.pk, rsin="123456782"
            )

        with self.subTest("update published with global config rsin"):
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(published.uuid)},
            )

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    detail_url,
                    {"publisher": str(new_publisher_without_rsin.uuid)},
                    headers=AUDIT_HEADERS,
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_update_document_rsin_delay.assert_called_with(
                document_id=published_document.pk, rsin="112345670"
            )

    @patch("woo_publications.publications.tasks.update_document_rsin.delay")
    def test_publication_regular_update_does_not_schedules_document_rsin_update_task(
        self, mock_update_document_rsin_delay: MagicMock
    ):
        publisher = OrganisationFactory.create(rsin="000000000", is_actief=True)
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept, publisher=publisher
        )
        published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published, publisher=publisher
        )
        DocumentFactory.create(
            publicatie=concept,
            publicatiestatus=PublicationStatusOptions.concept,
            with_registered_document=True,
        )
        DocumentFactory.create(
            publicatie=published,
            publicatiestatus=PublicationStatusOptions.published,
            with_registered_document=True,
        )

        with self.subTest("update concept with new publisher rsin"):
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(concept.uuid)},
            )

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    detail_url,
                    {"officieleTitel": "changed official title"},
                    headers=AUDIT_HEADERS,
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_update_document_rsin_delay.assert_not_called()

        with self.subTest("update published with global config rsin"):
            detail_url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(published.uuid)},
            )

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    detail_url,
                    {"officieleTitel": "changed official title"},
                    headers=AUDIT_HEADERS,
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_update_document_rsin_delay.assert_not_called()

    def test_publication_with_owner_group(self):
        org_unit = OrganisationUnitFactory.create(
            identifier="klachten", naam="Klachten"
        )
        publication = PublicationFactory.create(
            eigenaar=self.organisation_member,
            eigenaar_groep=org_unit,
            publicatiestatus=PublicationStatusOptions.concept,
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            archiefnominatie=ArchiveNominationChoices.retain,
            archiefactiedatum="2025-01-01",
        )

        with self.subTest("eigenaarGroep in list response"):
            list_response = self.client.get(
                reverse("api:publication-list"), headers=AUDIT_HEADERS
            )

            self.assertEqual(list_response.status_code, status.HTTP_200_OK)
            record = list_response.json()["results"][0]
            self.assertEqual(
                record["eigenaarGroep"],
                {
                    "identifier": "klachten",
                    "weergaveNaam": "Klachten",
                },
            )

        with self.subTest("eigenaarGroep in detail response"):
            detail_response = self.client.get(
                reverse("api:publication-detail", kwargs={"uuid": publication.uuid}),
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
            record = detail_response.json()
            self.assertEqual(
                record["eigenaarGroep"],
                {
                    "identifier": "klachten",
                    "weergaveNaam": "Klachten",
                },
            )


class PublicationApiRequiredFieldsTestCase(TokenAuthMixin, APITestCase):
    def test_create_concept_with_only_officiele_titel(self):
        url = reverse("api:publication-list")
        data = {
            "publicatiestatus": PublicationStatusOptions.concept,
            "officieleTitel": "title one",
        }

        response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_concept_with_only_officiele_titel(self):
        publication = PublicationFactory.create(
            officiele_titel="title one",
            publicatiestatus=PublicationStatusOptions.concept,
        )
        url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )
        data = {
            "publicatiestatus": PublicationStatusOptions.concept,
            "officieleTitel": "update",
        }

        response = self.client.put(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_publication_fields_empty(self):
        url = reverse("api:publication-list")
        with self.subTest("create concept publication doesn't raise errors"):
            data = {
                # required:
                "publicatiestatus": PublicationStatusOptions.concept,
                "officieleTitel": "title one",
                # allowed empty:
                "informatieCategorieen": [],
                "onderwerpen": [],
                "publisher": None,
                "verantwoordelijke": None,
                "opsteller": None,
                "kenmerken": [],
                "verkorteTitel": "",
                "omschrijving": "",
                "eigenaar": None,
                "eigenaarGroep": None,
                "bronBewaartermijn": "",
                "selectiecategorie": "",
                "archiefnominatie": "",
                "archiefactiedatum": None,
                "toelichtingBewaartermijn": "",
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        with self.subTest("validate 'empty value' data types"):
            data = {
                # required:
                "publicatiestatus": PublicationStatusOptions.concept,
                "officieleTitel": "title one",
                # allowed empty:
                "informatieCategorieen": None,  # must be list
                "onderwerpen": None,  # must be list
                # UUID string or null, but DRF allows empty string
                "publisher": "",
                # UUID string or null, but DRF allows empty string
                "verantwoordelijke": "",
                # UUID string or null, but DRF allows empty string
                "opsteller": "",
                "kenmerken": None,  # must be list
                "verkorteTitel": "",
                "omschrijving": "",
                "eigenaar": None,
                "eigenaarGroep": None,
                "bronBewaartermijn": "",
                "selectiecategorie": "",
                "archiefnominatie": "",
                "archiefactiedatum": None,
                "toelichtingBewaartermijn": "",
            }
            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            data = response.json()
            self.assertEqual(
                set(data.keys()),
                {
                    "informatieCategorieen",
                    "onderwerpen",
                    "kenmerken",
                },
            )
            self.assertEqual(response.data["informatie_categorieen"][0].code, "null")
            self.assertEqual(response.data["onderwerpen"][0].code, "null")
            self.assertEqual(response.data["kenmerken"][0].code, "null")

        with self.subTest("create published publication validates required fields"):
            data = {
                # required:
                "publicatiestatus": PublicationStatusOptions.published,
                "officieleTitel": "title one",
                # allowed empty:
                "informatieCategorieen": [],
                "onderwerpen": [],
                "publisher": None,
                "verantwoordelijke": None,
                "opsteller": None,
                "kenmerken": [],
                "verkorteTitel": "",
                "omschrijving": "",
                "eigenaar": None,
                "eigenaarGroep": None,
                "bronBewaartermijn": "",
                "selectiecategorie": "",
                "archiefnominatie": "",
                "archiefactiedatum": None,
                "toelichtingBewaartermijn": "",
            }

            response = self.client.post(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            data = response.json()
            self.assertEqual(set(data.keys()), {"informatieCategorieen", "publisher"})
            self.assertEqual(
                data["informatieCategorieen"], [_("This list may not be empty.")]
            )
            self.assertEqual(data["publisher"], [_("This field may not be null.")])

    def test_update_publication_fields_empty(self):
        organisation_member = OrganisationMemberFactory.create(
            identifier=AUDIT_HEADERS["AUDIT_USER_ID"],
            naam=AUDIT_HEADERS["AUDIT_USER_REPRESENTATION"],
        )
        with self.subTest("update with empty values doesn't raise errors"):
            publication = PublicationFactory.create(
                officiele_titel="title one",
                publicatiestatus=PublicationStatusOptions.concept,
                eigenaar=organisation_member,
            )
            url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(publication.uuid)},
            )

            data = {
                # required:
                "publicatiestatus": PublicationStatusOptions.concept,
                "officieleTitel": "update",
                # allowed empty:
                "informatieCategorieen": [],
                "onderwerpen": [],
                "publisher": "",
                "verantwoordelijke": "",
                "opsteller": "",
                "kenmerken": [],
                "verkorteTitel": "",
                "omschrijving": "",
                "eigenaar": None,
                "eigenaarGroep": None,
                "bronBewaartermijn": "",
                "selectiecategorie": "",
                "archiefnominatie": "",
                "archiefactiedatum": None,
                "toelichtingBewaartermijn": "",
            }

            response = self.client.put(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json()["eigenaar"],
                {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
            )

        with self.subTest("update fully empty values doesn't raise errors"):
            publication = PublicationFactory.create(
                officiele_titel="title one",
                publicatiestatus=PublicationStatusOptions.concept,
                eigenaar=organisation_member,
            )
            url = reverse(
                "api:publication-detail",
                kwargs={"uuid": str(publication.uuid)},
            )

            data = {
                # required:
                "publicatiestatus": PublicationStatusOptions.concept,
                "officieleTitel": "update",
                # allowed empty:
                "informatieCategorieen": [],
                "onderwerpen": [],
                "publisher": "",
                "verantwoordelijke": "",
                "opsteller": "",
                "kenmerken": [],
                "verkorteTitel": "",
                "omschrijving": "",
                "eigenaar": None,
                "eigenaarGroep": None,
                "bronBewaartermijn": "",
                "selectiecategorie": "",
                "archiefnominatie": "",
                "archiefactiedatum": None,
                "toelichtingBewaartermijn": "",
            }

            response = self.client.put(url, data, headers=AUDIT_HEADERS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json()["eigenaar"],
                {
                    "identifier": "id",
                    "weergaveNaam": "username",
                },
            )

    def test_create_publication_status_concept(self):
        url = reverse("api:publication-list")

        data = {
            "publicatiestatus": PublicationStatusOptions.concept,
        }

        response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"officieleTitel": [_("This field is required.")]}
        )

    def test_create_publication_status_publish(self):
        url = reverse("api:publication-list")

        data = {
            "publicatiestatus": PublicationStatusOptions.published,
        }

        response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "officieleTitel": [_("This field is required.")],
                "informatieCategorieen": [_("This field is required.")],
                "publisher": [_("This field is required.")],
            },
        )

    def test_update_publication_status_concept(self):
        publication = PublicationFactory.create(
            publisher=None,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "publicatiestatus": PublicationStatusOptions.concept,
            "officieleTitel": "",
        }

        response = self.client.put(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "officieleTitel": [_("This field may not be blank.")],
            },
        )

    def test_update_publication_status_publish(self):
        publication = PublicationFactory.create(
            publisher=None,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "publicatiestatus": PublicationStatusOptions.published,
            "officieleTitel": "",
        }

        response = self.client.put(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "officieleTitel": [_("This field may not be blank.")],
                "informatieCategorieen": [_("This field is required.")],
                "publisher": [_("This field is required.")],
            },
        )

    def test_update_publication_status_revoked(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.published,
        )
        url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "publicatiestatus": PublicationStatusOptions.revoked,
            "officieleTitel": "",
            "informatieCategorieen": [],
            "publisher": "",
        }

        response = self.client.put(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "officieleTitel": [_("This field may not be blank.")],
                "informatieCategorieen": [_("This list may not be empty.")],
                "publisher": [_("This field may not be null.")],
            },
        )
