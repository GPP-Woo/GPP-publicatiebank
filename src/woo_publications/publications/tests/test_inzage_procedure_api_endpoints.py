import datetime
from uuid import uuid4

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import (
    APIKeyUnAuthorizedMixin,
    TokenAuthMixin,
)

from ..constants import LegalRemedyOptions
from ..models import InzageProcedure
from .factories import InzageProcedureFactory, PublicationFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class InzageProcedureApiAuthorizationAndPermissionTests(
    APIKeyUnAuthorizedMixin, APITestCase
):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:inzageprocedure-list")
        detail_endpoint = reverse(
            "api:inzageprocedure-detail", kwargs={"uuid": str(uuid4())}
        )

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
        inzage_procedure = InzageProcedureFactory.create()
        list_url = reverse("api:inzageprocedure-list")
        detail_url = reverse(
            "api:inzageprocedure-detail",
            kwargs={"uuid": str(inzage_procedure.uuid)},
        )

        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPutEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPatchEndpointAccess(detail_url)
        self.assertWrongApiKeyProhibitsPostEndpointAccess(list_url)


class InzageProcedureApiTests(TokenAuthMixin, APITestCase):
    def test_list_inzage_procedure(self):
        publication_1, publication_2 = PublicationFactory.create_batch(2)
        inzage_procedure_1 = InzageProcedureFactory.create(
            publicatie=publication_1,
            url_bekendmaking="https://www.example.com/bekendmaking/one",
            toelichting="Some information about the first inzage procedure",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier/one",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 1),
        )
        inzage_procedure_2 = InzageProcedureFactory.create(
            publicatie=publication_2,
            url_bekendmaking="https://www.example.com/bekendmaking/two",
            toelichting="Some information about the second inzage procedure",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.perspective,
            url_reactieformulier="https://www.example.com/reactieformulier/two",
            datum_begin_inzagetermijn=datetime.date(2020, 12, 31),
            datum_einde_inzagetermijn=datetime.date(2025, 12, 31),
        )

        response = self.client.get(
            reverse("api:inzageprocedure-list"), headers=AUDIT_HEADERS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

        with self.subTest("first_item_in_response_with_expected_data"):
            expected_first_item_data = {
                "uuid": str(inzage_procedure_2.uuid),
                "publicatie": str(publication_2.uuid),
                "urlBekendmaking": "https://www.example.com/bekendmaking/two",
                "toelichting": "Some information about the second inzage procedure",
                "beschikbaarRechtsmiddel": LegalRemedyOptions.perspective,
                "urlReactieformulier": "https://www.example.com/reactieformulier/two",
                "datumBeginInzagetermijn": "2020-12-31",
                "datumEindeInzagetermijn": "2025-12-31",
                "automatischIntrekken": False,
            }

            self.assertEqual(data["results"][0], expected_first_item_data)

        with self.subTest("second_item_in_response_with_expected_data"):
            expected_second_item_data = {
                "uuid": str(inzage_procedure_1.uuid),
                "publicatie": str(publication_1.uuid),
                "urlBekendmaking": "https://www.example.com/bekendmaking/one",
                "toelichting": "Some information about the first inzage procedure",
                "beschikbaarRechtsmiddel": LegalRemedyOptions.objection,
                "urlReactieformulier": "https://www.example.com/reactieformulier/one",
                "datumBeginInzagetermijn": "2020-01-01",
                "datumEindeInzagetermijn": "2025-01-01",
                "automatischIntrekken": False,
            }

            self.assertEqual(data["results"][1], expected_second_item_data)

    def test_list_inzage_procedure_filter_order(self):
        publication_1, publication_2 = PublicationFactory.create_batch(2)
        InzageProcedureFactory.create(
            publicatie=publication_1,
            url_bekendmaking="https://www.example.com/bekendmaking/one",
            toelichting="Some information about the first inzage procedure",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier/one",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 1),
        )
        inzage_procedure_2 = InzageProcedureFactory.create(
            publicatie=publication_2,
            url_bekendmaking="https://www.example.com/bekendmaking/two",
            toelichting="Some information about the second inzage procedure",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.perspective,
            url_reactieformulier="https://www.example.com/reactieformulier/two",
            datum_begin_inzagetermijn=datetime.date(2020, 12, 31),
            datum_einde_inzagetermijn=datetime.date(2025, 12, 31),
        )

        response = self.client.get(
            reverse("api:inzageprocedure-list"),
            {"publicatie": str(publication_2.uuid)},
            headers=AUDIT_HEADERS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(
            data["results"][0],
            {
                "uuid": str(inzage_procedure_2.uuid),
                "publicatie": str(publication_2.uuid),
                "urlBekendmaking": "https://www.example.com/bekendmaking/two",
                "toelichting": "Some information about the second inzage procedure",
                "beschikbaarRechtsmiddel": LegalRemedyOptions.perspective,
                "urlReactieformulier": "https://www.example.com/reactieformulier/two",
                "datumBeginInzagetermijn": "2020-12-31",
                "datumEindeInzagetermijn": "2025-12-31",
                "automatischIntrekken": False,
            },
        )

    def test_detail_inzage_procedure(self):
        publication = PublicationFactory.create()
        inzage_procedure = InzageProcedureFactory.create(
            publicatie=publication,
            url_bekendmaking="https://www.example.com/bekendmaking/one",
            toelichting="Some information about the first inzage procedure",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier/one",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 1),
        )
        detail_url = reverse(
            "api:inzageprocedure-detail",
            kwargs={"uuid": str(inzage_procedure.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_first_item_data = {
            "uuid": str(inzage_procedure.uuid),
            "publicatie": str(publication.uuid),
            "urlBekendmaking": "https://www.example.com/bekendmaking/one",
            "toelichting": "Some information about the first inzage procedure",
            "beschikbaarRechtsmiddel": LegalRemedyOptions.objection,
            "urlReactieformulier": "https://www.example.com/reactieformulier/one",
            "datumBeginInzagetermijn": "2020-01-01",
            "datumEindeInzagetermijn": "2025-01-01",
            "automatischIntrekken": False,
        }

        self.assertEqual(data, expected_first_item_data)

    def test_create_inzage_procedure(self):
        assert InzageProcedure.objects.count() == 0

        publication = PublicationFactory.create()
        url = reverse("api:inzageprocedure-list")
        body = {
            "publicatie": str(publication.uuid),
            "urlBekendmaking": "https://www.example.com/bekendmaking",
            "toelichting": "toelichting",
            "beschikbaarRechtsmiddel": LegalRemedyOptions.objection,
            "urlReactieformulier": "https://www.example.com/reactieformulier",
            "datumBeginInzagetermijn": "2020-01-01",
            "datumEindeInzagetermijn": "2025-01-02",
            "automatischIntrekken": True,
        }

        response = self.client.post(url, data=body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # checks if the object was successfully created.
        inzage_procedure = InzageProcedure.objects.filter(
            publicatie=publication,
            url_bekendmaking="https://www.example.com/bekendmaking",
            toelichting="toelichting",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier",
            datum_begin_inzagetermijn="2020-01-01",
            datum_einde_inzagetermijn="2025-01-02",
        )
        self.assertTrue(inzage_procedure.exists())

        inzage_procedure = inzage_procedure.first()
        assert inzage_procedure
        response_data = response.json()

        self.assertEqual(response_data, {"uuid": str(inzage_procedure.uuid), **body})

    def test_end_date_auto_selects_workday(self):
        assert InzageProcedure.objects.count() == 0

        publication = PublicationFactory.create()
        url = reverse("api:inzageprocedure-list")
        body = {
            "publicatie": str(publication.uuid),
            "urlBekendmaking": "https://www.example.com/bekendmaking",
            "toelichting": "toelichting",
            "beschikbaarRechtsmiddel": LegalRemedyOptions.objection,
            "urlReactieformulier": "https://www.example.com/reactieformulier",
            "datumBeginInzagetermijn": "2020-01-01",
            "datumEindeInzagetermijn": "2026-04-27",
            "automatischIntrekken": True,
        }

        response = self.client.post(url, data=body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["datumEindeInzagetermijn"], "2026-04-28")

    def test_update_inzage_procedure(self):
        assert InzageProcedure.objects.count() == 0

        publication_1, publication_2 = PublicationFactory.create_batch(2)
        inzage_procedure = InzageProcedureFactory.create(
            publicatie=publication_1,
            url_bekendmaking="https://www.example.com/bekendmaking/one",
            toelichting="Some information about the first inzage procedure",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier/one",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 2),
            automatisch_intrekken=False,
        )
        detail_url = reverse(
            "api:inzageprocedure-detail",
            kwargs={"uuid": str(inzage_procedure.uuid)},
        )
        body = {
            "publicatie": str(publication_2.uuid),
            "urlBekendmaking": "https://www.example.com/bekendmaking/changed",
            "toelichting": "changed",
            "beschikbaarRechtsmiddel": LegalRemedyOptions.perspective,
            "urlReactieformulier": "https://www.example.com/reactieformulier/changed",
            "datumBeginInzagetermijn": "2000-01-01",
            "datumEindeInzagetermijn": "2015-01-02",
            "automatischIntrekken": True,
        }

        response = self.client.put(detail_url, data=body, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, {"uuid": str(inzage_procedure.uuid), **body})

    def test_partially_update_inzage_procedure(self):
        assert InzageProcedure.objects.count() == 0

        publication_1, publication_2 = PublicationFactory.create_batch(2)
        inzage_procedure = InzageProcedureFactory.create(
            publicatie=publication_1,
            url_bekendmaking="https://www.example.com/bekendmaking",
            toelichting="Some information",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            url_reactieformulier="https://www.example.com/reactieformulier",
            datum_begin_inzagetermijn=datetime.date(2020, 1, 1),
            datum_einde_inzagetermijn=datetime.date(2025, 1, 1),
            automatisch_intrekken=False,
        )
        detail_url = reverse(
            "api:inzageprocedure-detail",
            kwargs={"uuid": str(inzage_procedure.uuid)},
        )

        response = self.client.patch(
            detail_url, data={"automatischIntrekken": True}, headers=AUDIT_HEADERS
        )

        expected_data = {
            "uuid": str(inzage_procedure.uuid),
            "publicatie": str(publication_1.uuid),
            "urlBekendmaking": "https://www.example.com/bekendmaking",
            "toelichting": "Some information",
            "beschikbaarRechtsmiddel": LegalRemedyOptions.objection,
            "urlReactieformulier": "https://www.example.com/reactieformulier",
            "datumBeginInzagetermijn": "2020-01-01",
            "datumEindeInzagetermijn": "2025-01-01",
            # the altered data
            "automatischIntrekken": True,
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, expected_data)

    def test_destroy_inzage_procedure(self):
        inzage_procedure = InzageProcedureFactory.create()
        detail_url = reverse(
            "api:inzageprocedure-detail",
            kwargs={"uuid": str(inzage_procedure.uuid)},
        )

        response = self.client.delete(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            InzageProcedure.objects.filter(uuid=inzage_procedure.uuid).exists()
        )
