from uuid import uuid4

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from woo_publications.contrib.documents_api.api import DUMMY_IC_UUID
from woo_publications.metadata.tests.factories import InformationCategoryFactory


class CatalogiAPIDocumentTypeViewTests(APITestCase):
    def test_information_category_exposed_as_documenttype(self):
        information_category = InformationCategoryFactory.create(
            identifier=(
                "https://generiek-publicatieplatform.woo/informatiecategorie/"
                "f083a7d1-de29-46f9-98d5-677a8e27ebfb"
            ),
            naam="Raadsbesluit",
            definitie="Besluit vastgesteld tijdens raadsvergaderingen.",
        )
        endpoint = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": information_category.uuid},
        )

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            "url": f"http://testserver{endpoint}",
            "catalogus": "http://testserver/catalogi/api/v1/catalogussen/-fake-",
            "omschrijving": "Raadsbesluit",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2024-09-01",
            "concept": False,
            "informatieobjectcategorie": "Wet Open Overheid",
            "besluittypen": [],
            "zaaktypen": [],
        }
        self.assertEqual(response.json(), expected_data)

    def test_dummy_information_category_exposed_as_documenttype(self):
        endpoint = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": DUMMY_IC_UUID},
        )

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_data = {
            "url": f"http://testserver{endpoint}",
            "catalogus": "http://testserver/catalogi/api/v1/catalogussen/-fake-",
            "omschrijving": "",
            "vertrouwelijkheidaanduiding": "openbaar",
            "beginGeldigheid": "2024-09-01",
            "concept": False,
            "informatieobjectcategorie": "Wet Open Overheid",
            "besluittypen": [],
            "zaaktypen": [],
        }
        self.assertEqual(response.json(), expected_data)

    def test_404_for_bad_uuid_reference(self):
        endpoint = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": str(uuid4())},
        )

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
