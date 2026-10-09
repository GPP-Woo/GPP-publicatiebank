import re
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase
from django.utils.translation import gettext as _

import requests_mock
from requests.exceptions import RequestException
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..client import CatalogiAPIError, get_client
from .constants import DEFAULT_CATALOGUS

openbaar = VertrouwelijkheidsAanduidingen.openbaar


class CatalogiClientTests(VCRMixin, TestCase):
    def test_create_catalogi(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client:
            catalogi = client.create_catalogi(rsin="571586685")

        self.assertIsInstance(catalogi, str)

        with self.subTest("check catalogi is created"):
            # and we expect that we can fetch the Catalogi too
            detail_response = client.get(catalogi)

            self.assertEqual(detail_response.status_code, 200)

    def test_create_catalogi_request_error(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with (
            get_client(service) as client,
            self.assertRaisesMessage(
                CatalogiAPIError, "Catalogus couldn't be created."
            ),
            self.vcr_raises(RequestException),
        ):
            client.create_catalogi(rsin="123456782")

    def test_get_iot_by_description(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)
        with get_client(service) as client:
            with self.subTest("concept"):
                response = client.post(
                    "informatieobjecttypen",
                    json={
                        "catalogus": DEFAULT_CATALOGUS,
                        "omschrijving": "SOME-RANDOM-DESCRIPTION-OF-A-CONCEPT-IOT",
                        "vertrouwelijkheidaanduiding": openbaar,
                        "beginGeldigheid": "2024-09-01",
                        "informatieobjectcategorie": "Wet Open Overheid",
                    },
                )
                assert response.status_code == 201

                iot = client.get_iot_by_description(
                    catalogus=DEFAULT_CATALOGUS,
                    description="SOME-RANDOM-DESCRIPTION-OF-A-CONCEPT-IOT",
                )
                self.assertIsNone(iot)

            with self.subTest("published"):
                response = client.post(
                    "informatieobjecttypen",
                    json={
                        "catalogus": DEFAULT_CATALOGUS,
                        "omschrijving": "SOME-RANDOM-DESCRIPTION-OF-A-PUBLISHED-IOT",
                        "vertrouwelijkheidaanduiding": openbaar,
                        "beginGeldigheid": "2024-09-01",
                        "informatieobjectcategorie": "Wet Open Overheid",
                    },
                )
                assert response.status_code == 201
                iot_url = response.json()["url"]

                response = client.post(iot_url + "/publish")
                assert response.status_code == 200

                iot = client.get_iot_by_description(
                    catalogus=DEFAULT_CATALOGUS,
                    description="SOME-RANDOM-DESCRIPTION-OF-A-PUBLISHED-IOT",
                )
                assert iot
                self.assertEqual(iot.url, iot_url)

    def test_get_iot_by_description_error(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)
        with (
            get_client(service) as client,
            self.assertRaisesMessage(
                CatalogiAPIError,
                _("Something went wrong while trying to retrieving IOT."),
            ),
            self.vcr_raises(RequestException),
        ):
            client.get_iot_by_description(
                catalogus=DEFAULT_CATALOGUS,
                description="oops-all-errors",
            )

    def test_create_iot(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client:
            iot = client.create_iot(
                catalogus=DEFAULT_CATALOGUS,
                description="create iot.",
                confidentiality_indication=openbaar,
            )

        self.assertGreater(len(str(iot.uuid)), 0)
        self.assertIsInstance(iot.url, str)

        with self.subTest("check iot is created and published"):
            # and we expect that we can fetch the IOT too
            detail_response = client.get(iot.url)

            self.assertEqual(detail_response.status_code, 200)
            # ensure that the IOT is published
            self.assertFalse(detail_response.json()["concept"])

    def test_create_iot_returns_existing_iot(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client:
            response = client.post(
                "informatieobjecttypen",
                json={
                    "catalogus": DEFAULT_CATALOGUS,
                    "omschrijving": "LETS-RETRIEVE-AN-EXISTING-IOT",
                    "vertrouwelijkheidaanduiding": openbaar,
                    "beginGeldigheid": "2024-09-01",
                    "informatieobjectcategorie": "Wet Open Overheid",
                },
            )
            assert response.status_code == 201
            iot_url = response.json()["url"]

            response = client.post(iot_url + "/publish")
            assert response.status_code == 200

            iot = client.create_iot(
                catalogus=DEFAULT_CATALOGUS,
                description="LETS-RETRIEVE-AN-EXISTING-IOT",
                confidentiality_indication=openbaar,
            )
            self.assertEqual(iot.url, iot_url)

    def test_while_encountering_error_during_publishing_deleted_iot(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client, requests_mock.Mocker(real_http=True) as m:
            m.post(
                re.compile(
                    r"http://openzaak.docker.internal:8001/catalogi/api/v1/informatieobjecttypen/[^/]+/publish"
                ),
                status_code=400,
            )
            with self.assertRaisesMessage(
                CatalogiAPIError, _("IOT object couldn't be published.")
            ):
                client.create_iot(
                    catalogus=DEFAULT_CATALOGUS,
                    description="encountering error during publishing deleted iot.",
                    confidentiality_indication=openbaar,
                )

        with self.subTest("check no concept IOT's exist"):
            detail_response = client.get(
                "informatieobjecttypen",
                params={
                    "status": "concept",
                    "omschrijving": "encountering error during publishing deleted iot.",
                },
            )

            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["count"], 0)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.get_iot_by_description",
        return_value=None,
    )
    def test_error_during_creating_iot(self, mock_get_iot_by_description: MagicMock):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with (
            get_client(service) as client,
            self.assertRaisesMessage(
                CatalogiAPIError, _("Something went wrong while creating IOT.")
            ),
            self.vcr_raises(RequestException),
        ):
            client.create_iot(
                catalogus=DEFAULT_CATALOGUS,
                description="error during creating iot",
                confidentiality_indication=openbaar,
            )

    def test_destroy_iot(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client:
            iot = client.create_iot(
                catalogus=DEFAULT_CATALOGUS,
                description="destroy iot.",
                confidentiality_indication=openbaar,
            )
            client.destroy_iot(uuid=iot.uuid)

        with self.subTest("check no concept IOT's exist"):
            detail_response = client.get(iot.url)

            self.assertEqual(detail_response.status_code, 404)

    def test_destroy_iot_error(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client:
            iot = client.create_iot(
                catalogus=DEFAULT_CATALOGUS,
                description="destroy iot error.",
                confidentiality_indication=openbaar,
            )

            with (
                self.assertRaisesMessage(
                    CatalogiAPIError, _("Something went wrong while deleting the IOT.")
                ),
                self.vcr_raises(RequestException),
            ):
                client.destroy_iot(uuid=iot.uuid)

    def test_destroy_iot_when_iot_does_not_exist(self):
        service = ServiceFactory.build(for_catalogi_api_docker_compose=True)

        with get_client(service) as client:
            client.destroy_iot(uuid=UUID("e2016928-ca1b-4b08-911b-a2495b234eb6"))
