import datetime
import tempfile

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.constants import (
    InformationCategoryOrigins,
    OrganisationOrigins,
)
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
    ThemeFactory,
)
from woo_publications.publications.constants import (
    LegalProcedureOptions,
    PublicationStatusOptions,
)
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    InzageProcedureFactory,
    PublicationFactory,
    TopicFactory,
)

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "Ophidian",
    "AUDIT_USER_ID": "D12R9IUIcIw",
    "AUDIT_REMARKS": "Ophidian - PRSPCT XL 21 Podcast",
}


class PublicationApiTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=AUDIT_HEADERS["AUDIT_USER_ID"],
            naam=AUDIT_HEADERS["AUDIT_USER_REPRESENTATION"],
        )

    def test_list_publications(self):
        ic = InformationCategoryFactory.create(naam="Mind Control")
        topic = TopicFactory.create(officiele_titel="Kraken")
        organisation = OrganisationFactory.create(naam="Trammelant")

        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
        )
        InzageProcedureFactory.create(publicatie=concept)

        with freeze_time("2024-09-25T12:30:00-00:00"):
            published = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                eigenaar=self.organisation_member,
                informatie_categorieen=[ic],
                onderwerpen=[topic],
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="Our Potential",
                verkorte_titel="Lose Yourself",
                omschrijving="Borrowed Time.",
                bron_bewaartermijn="Desolation",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        inzage_procedure = InzageProcedureFactory.create(
            publicatie=published,
            url_bekendmaking="https://www.example.com/bekendmaking/one",
            toelichting="Bass In The Place",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier/one",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 1),
        )

        revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
        )
        InzageProcedureFactory.create(publicatie=revoked)
        revoked.publicatiestatus = PublicationStatusOptions.revoked
        revoked.save()

        response = self.client.get(reverse("researcher:publication-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            "uuid": str(published.uuid),
            "urlPublicatieExtern": "",
            "officieleTitel": "Our Potential",
            "verkorteTitel": "Lose Yourself",
            "omschrijving": "Borrowed Time.",
            "informatieCategorieen": [str(ic.uuid)],
            "diWooInformatieCategorieen": None,
            "onderwerpen": [str(topic.uuid)],
            "publisher": str(organisation.uuid),
            "verantwoordelijke": str(organisation.uuid),
            "opsteller": str(organisation.uuid),
            "kenmerken": [],
            "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "datumBeginGeldigheid": None,
            "datumEindeGeldigheid": None,
            "inzageProcedure": {
                "uuid": str(inzage_procedure.uuid),
                "urlBekendmaking": "https://www.example.com/bekendmaking/one",
                "toelichting": "Bass In The Place",
                "beschikbaarRechtsmiddel": LegalProcedureOptions.objection,
                "urlReactieformulier": "https://www.example.com/reactieformulier/one",
                "datumBeginInzagetermijn": "2020-01-01",
                "datumEindeInzagetermijn": "2025-01-01",
                "automatischIntrekken": False,
            },
        }
        self.assertEqual(response.json()["results"], [expected_data])

    def test_detail_publications(self):
        ic = InformationCategoryFactory.create(naam="Mind Control")
        topic = TopicFactory.create(officiele_titel="Kraken")
        organisation = OrganisationFactory.create(naam="Trammelant")

        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
        )

        with freeze_time("2024-09-25T12:30:00-00:00"):
            published = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                eigenaar=self.organisation_member,
                informatie_categorieen=[ic],
                onderwerpen=[topic],
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="Our Potential",
                verkorte_titel="Lose Yourself",
                omschrijving="Borrowed Time.",
                bron_bewaartermijn="Desolation",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        inzage_procedure = InzageProcedureFactory.create(
            publicatie=published,
            url_bekendmaking="https://www.example.com/bekendmaking/one",
            toelichting="Bass In The Place",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier/one",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 1),
        )

        revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
        )
        revoked.publicatiestatus = PublicationStatusOptions.revoked
        revoked.save()

        with self.subTest("published publication shows up"):
            response = self.client.get(
                reverse(
                    "researcher:publication-detail", kwargs={"uuid": published.uuid}
                )
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            expected_data = {
                "uuid": str(published.uuid),
                "urlPublicatieExtern": "",
                "officieleTitel": "Our Potential",
                "verkorteTitel": "Lose Yourself",
                "omschrijving": "Borrowed Time.",
                "informatieCategorieen": [str(ic.uuid)],
                "diWooInformatieCategorieen": None,
                "onderwerpen": [str(topic.uuid)],
                "publisher": str(organisation.uuid),
                "verantwoordelijke": str(organisation.uuid),
                "opsteller": str(organisation.uuid),
                "kenmerken": [],
                "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
                "datumBeginGeldigheid": None,
                "datumEindeGeldigheid": None,
                "inzageProcedure": {
                    "uuid": str(inzage_procedure.uuid),
                    "urlBekendmaking": "https://www.example.com/bekendmaking/one",
                    "toelichting": "Bass In The Place",
                    "beschikbaarRechtsmiddel": LegalProcedureOptions.objection,
                    "urlReactieformulier": "https://www.example.com/reactieformulier/one",
                    "datumBeginInzagetermijn": "2020-01-01",
                    "datumEindeInzagetermijn": "2025-01-01",
                    "automatischIntrekken": False,
                },
            }

            self.assertEqual(response.json(), expected_data)

        with self.subTest("concept publication does not show up"):
            response = self.client.get(
                reverse("researcher:publication-detail", kwargs={"uuid": concept.uuid})
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.subTest("revoked publication does not show up"):
            response = self.client.get(
                reverse("researcher:publication-detail", kwargs={"uuid": revoked.uuid})
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DocumentApiTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=AUDIT_HEADERS["AUDIT_USER_ID"],
            naam=AUDIT_HEADERS["AUDIT_USER_REPRESENTATION"],
        )

    def test_list_documents(self):
        organisation = OrganisationFactory.create()
        publication_concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
        )
        DocumentFactory.create(
            publicatie=publication_concept,
            publicatiestatus=PublicationStatusOptions.concept,
            upload_complete=True,
        )

        publication_published = PublicationFactory.create(
            verantwoordelijke=organisation,
            eigenaar=self.organisation_member,
            publicatiestatus=PublicationStatusOptions.published,
        )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document_published = DocumentFactory.create(
                publicatie=publication_published,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="The Last Great Overdose",
                officiele_titel="Trapped",
                verkorte_titel="Endless Blackness",
                omschrijving="Universal Threat",
                creatiedatum="2024-01-01",
                datum_ondertekend=None,
                ontvangstdatum=timezone.now(),
                source_url="https://www.example.com/bla",
                upload_complete=True,
            )

        publication_revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
        )
        DocumentFactory.create(
            publicatie=publication_revoked,
            upload_complete=True,
        )
        publication_revoked.revoke(user=UserFactory.create())
        publication_revoked.save()

        response = self.client.get(reverse("researcher:document-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            "uuid": str(document_published.uuid),
            "identifier": "The Last Great Overdose",
            "publicatie": str(publication_published.uuid),
            "officieleTitel": "Trapped",
            "verkorteTitel": "Endless Blackness",
            "omschrijving": "Universal Threat",
            "kenmerken": [],
            "creatiedatum": "2024-01-01",
            "ontvangstdatum": "2024-09-25T14:30:00+02:00",
            "datumOndertekend": None,
            "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
            "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
            "bestandsformaat": "unknown",
            "bestandsnaam": "unknown.bin",
            "bestandsomvang": 0,
            "documentUrl": "https://www.example.com/bla",
        }
        self.assertEqual(response.json()["results"], [expected_data])

    def test_detail_documents(self):
        organisation = OrganisationFactory.create()
        publication_concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
        )
        document_concept = DocumentFactory.create(
            publicatie=publication_concept,
            publicatiestatus=PublicationStatusOptions.concept,
            upload_complete=True,
        )

        publication_published = PublicationFactory.create(
            verantwoordelijke=organisation,
            eigenaar=self.organisation_member,
            publicatiestatus=PublicationStatusOptions.published,
        )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document_published = DocumentFactory.create(
                publicatie=publication_published,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="The Last Great Overdose",
                officiele_titel="Trapped",
                verkorte_titel="Endless Blackness",
                omschrijving="Universal Threat",
                creatiedatum="2024-01-01",
                datum_ondertekend=None,
                ontvangstdatum=timezone.now(),
                source_url="https://www.example.com/bla",
                upload_complete=True,
            )

        publication_revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
        )
        document_revoked = DocumentFactory.create(
            publicatie=publication_revoked,
            upload_complete=True,
        )
        publication_revoked.revoke(user=UserFactory.create())
        publication_revoked.save()

        with self.subTest("published document show up"):
            response = self.client.get(
                reverse(
                    "researcher:document-detail",
                    kwargs={"uuid": document_published.uuid},
                ),
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            expected_data = {
                "uuid": str(document_published.uuid),
                "identifier": "The Last Great Overdose",
                "publicatie": str(publication_published.uuid),
                "officieleTitel": "Trapped",
                "verkorteTitel": "Endless Blackness",
                "omschrijving": "Universal Threat",
                "kenmerken": [],
                "creatiedatum": "2024-01-01",
                "ontvangstdatum": "2024-09-25T14:30:00+02:00",
                "datumOndertekend": None,
                "gepubliceerdOp": "2024-09-25T14:30:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:30:00+02:00",
                "bestandsformaat": "unknown",
                "bestandsnaam": "unknown.bin",
                "bestandsomvang": 0,
                "documentUrl": "https://www.example.com/bla",
            }
            self.assertEqual(response.json(), expected_data)

        with self.subTest("concept document does not show up"):
            response = self.client.get(
                reverse(
                    "researcher:document-detail",
                    kwargs={"uuid": document_concept.uuid},
                )
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.subTest("revoked document does not show up"):
            response = self.client.get(
                reverse(
                    "researcher:document-detail",
                    kwargs={"uuid": document_revoked.uuid},
                )
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TopicApiTestCase(APITestCase):
    def test_list_topics(self):
        with freeze_time("2024-09-25T12:00:00-00:00"):
            published = TopicFactory.create(
                officiele_titel="Noise Pumper",
                omschrijving="Trespasser",
                publicatiestatus=PublicationStatusOptions.published,
                promoot=True,
            )
        concept = TopicFactory.create(publicatiestatus=PublicationStatusOptions.concept)
        revoked = TopicFactory.create(publicatiestatus=PublicationStatusOptions.revoked)

        PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
            onderwerpen=[concept, published, revoked],
        )
        publication_published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            onderwerpen=[concept, published, revoked],
        )
        publication_revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            onderwerpen=[concept, published, revoked],
        )
        publication_revoked.revoke(user=UserFactory.create())
        publication_revoked.save()

        response = self.client.get(reverse("researcher:topic-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            "uuid": str(published.uuid),
            "afbeelding": f"http://testserver{published.afbeelding.url}",
            "publicaties": [str(publication_published.uuid)],
            "officieleTitel": "Noise Pumper",
            "omschrijving": "Trespasser",
            "laatstGewijzigdDatum": "2024-09-25T14:00:00+02:00",
        }
        self.assertEqual(response.json()["results"], [expected_data])

    def test_detail_topics(self):
        with freeze_time("2024-09-25T12:00:00-00:00"):
            published = TopicFactory.create(
                officiele_titel="Noise Pumper",
                omschrijving="Trespasser",
                publicatiestatus=PublicationStatusOptions.published,
                promoot=True,
            )
        concept = TopicFactory.create(publicatiestatus=PublicationStatusOptions.concept)
        revoked = TopicFactory.create(publicatiestatus=PublicationStatusOptions.revoked)

        with self.subTest("published topics show up"):
            response = self.client.get(
                reverse("researcher:topic-detail", kwargs={"uuid": published.uuid})
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            expected_data = {
                "uuid": str(published.uuid),
                "afbeelding": f"http://testserver{published.afbeelding.url}",
                "publicaties": [],
                "officieleTitel": "Noise Pumper",
                "omschrijving": "Trespasser",
                "laatstGewijzigdDatum": "2024-09-25T14:00:00+02:00",
            }
            self.assertEqual(response.json(), expected_data)

        with self.subTest("concept topic does not show up"):
            response = self.client.get(
                reverse("researcher:topic-detail", kwargs={"uuid": concept.uuid})
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.subTest("revoked topic does not show up"):
            response = self.client.get(
                reverse("researcher:topic-detail", kwargs={"uuid": revoked.uuid})
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OrganisationApiTests(APITestCase):
    def test_list_organisations(self):
        OrganisationFactory.create(
            naam="id",
            identifier="https://www.example.com/organisaties/1",
            oorsprong=OrganisationOrigins.custom_entry,
            is_actief=False,
        )
        active = OrganisationFactory.create(
            naam="Crisis Situation",
            identifier="https://www.example.com/organisaties/2",
            oorsprong=OrganisationOrigins.municipality_list,
            is_actief=True,
        )

        response = self.client.get(reverse("researcher:organisation-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            "uuid": str(active.uuid),
            "identifier": "https://www.example.com/organisaties/2",
            "naam": "Crisis Situation",
            "oorsprong": OrganisationOrigins.municipality_list,
        }
        self.assertEqual(response.json()["results"], [expected_data])

    def test_detail_organisations(self):
        inactive = OrganisationFactory.create(
            naam="id",
            identifier="https://www.example.com/organisaties/1",
            oorsprong=OrganisationOrigins.custom_entry,
            is_actief=False,
        )
        active = OrganisationFactory.create(
            naam="Crisis Situation",
            identifier="https://www.example.com/organisaties/2",
            oorsprong=OrganisationOrigins.municipality_list,
            is_actief=True,
        )

        with self.subTest("active org shows up"):
            response = self.client.get(
                reverse("researcher:organisation-detail", kwargs={"uuid": active.uuid})
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            expected_data = {
                "uuid": str(active.uuid),
                "identifier": "https://www.example.com/organisaties/2",
                "naam": "Crisis Situation",
                "oorsprong": OrganisationOrigins.municipality_list,
            }
            self.assertEqual(response.json(), expected_data)

        with self.subTest("inactive org does not show up"):
            response = self.client.get(
                reverse(
                    "researcher:organisation-detail", kwargs={"uuid": inactive.uuid}
                )
            )

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class InformationCategoryTests(APITestCase):
    def test_list_informatie_categorie(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            naam_meervoud="first items",
            definitie="This is some information about the first item.",
            order=0,
            oorsprong=InformationCategoryOrigins.value_list,
        )
        information_category2 = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            naam_meervoud="second items",
            omschrijving="bla bla bla",
            definitie="This is some information about the second item.",
            order=1,
            oorsprong=InformationCategoryOrigins.custom_entry,
        )

        response = self.client.get(reverse("researcher:informationcategory-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 2)

        with self.subTest("first item in response with expected_data"):
            expected_first_item_data = {
                "uuid": str(information_category.uuid),
                "identifier": "https://www.example.com/waardenlijsten/1",
                "naam": "first item",
                "naamMeervoud": "first items",
                "omschrijving": "",
                "definitie": "This is some information about the first item.",
                "order": 0,
                "oorsprong": InformationCategoryOrigins.value_list,
            }
            self.assertEqual(data["results"][0], expected_first_item_data)

        with self.subTest("second item in response with expected_data"):
            expected_second_item_data = {
                "uuid": str(information_category2.uuid),
                "identifier": "https://www.example.com/waardenlijsten/2",
                "naam": "second item",
                "naamMeervoud": "second items",
                "omschrijving": "bla bla bla",
                "definitie": "This is some information about the second item.",
                "order": 1,
                "oorsprong": InformationCategoryOrigins.custom_entry,
            }
            self.assertEqual(data["results"][1], expected_second_item_data)

    def test_detail_informatie_categorie(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            naam_meervoud="first items",
            omschrijving="bla bla bla",
            definitie="This is some information about the first item.",
            order=0,
            oorsprong=InformationCategoryOrigins.value_list,
        )
        detail_url = reverse(
            "researcher:informationcategory-detail",
            kwargs={"uuid": str(information_category.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        expected_data = {
            "uuid": str(information_category.uuid),
            "identifier": "https://www.example.com/waardenlijsten/1",
            "naam": "first item",
            "naamMeervoud": "first items",
            "omschrijving": "bla bla bla",
            "definitie": "This is some information about the first item.",
            "order": 0,
            "oorsprong": InformationCategoryOrigins.value_list,
        }
        self.assertEqual(data, expected_data)


class ThemeTests(APITestCase):
    def test_list_theme(self):
        parent_theme = ThemeFactory.create(
            identifier="https://www.example.com/thema/1",
            naam="first item",
        )
        child_theme = ThemeFactory.create(
            identifier="https://www.example.com/thema/2",
            naam="second item",
            parent=parent_theme,
        )
        list_url = reverse("researcher:theme-list")

        response = self.client.get(list_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)

        expected_second_item_data = {
            "uuid": str(child_theme.uuid),
            "identifier": "https://www.example.com/thema/2",
            "naam": "second item",
            "subThemes": [],
        }

        expected_first_item_data = {
            "uuid": str(parent_theme.uuid),
            "identifier": "https://www.example.com/thema/1",
            "naam": "first item",
            "subThemes": [
                expected_second_item_data,
            ],
        }

        with self.subTest("first item in response with expected_data"):
            self.assertEqual(data["results"], [expected_first_item_data])

    def test_detail_theme(self):
        theme = ThemeFactory.create(
            identifier="https://www.example.com/thema/1",
            naam="item one",
        )
        list_url = reverse(
            "researcher:theme-detail",
            kwargs={"uuid": str(theme.uuid)},
        )

        response = self.client.get(list_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        expected_data = {
            "uuid": str(theme.uuid),
            "identifier": "https://www.example.com/thema/1",
            "naam": "item one",
            "subThemes": [],
        }

        self.assertEqual(data, expected_data)
