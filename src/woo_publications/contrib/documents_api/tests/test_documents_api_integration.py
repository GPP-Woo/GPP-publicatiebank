"""
Test the high level integration with the Documents API.

These tests validate that:

* the docker-compose configuration is functional to develop against
* it's possible to register a document in the Documents API with a document type
  ('informatieobjecttype') pointing back to woo-publications

The API traffic is captured and 'mocked' using VCR.py. When re-recording the cassettes
for these tests, make sure to bring up the docker compose in the root of the repo:

.. code-block:: bash

    docker compose up

See ``docker/open-zaak/README.md`` for the test credentials and available data.
"""

from django.test import LiveServerTestCase

from furl import furl
from rest_framework.reverse import reverse
from zgw_consumers.client import build_client

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..api import DUMMY_IC_UUID


class DocumentsApiIntegrationTests(VCRMixin, LiveServerTestCase):
    # host and port must match the service declared in
    # docker/open-zaak/fixtures/configuration.json
    host = "0.0.0.0"
    port = 8100

    def setUp(self):
        super().setUp()

        self.documents_api_service = ServiceFactory.build(
            for_documents_api_docker_compose=True
        )

    def test_can_create_document_with_woo_publications_informatieobjecttype(self):
        information_category = InformationCategoryFactory.create()
        iot_path = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": information_category.uuid},
        )
        iot_url = (
            furl(self.live_server_url.replace("0.0.0.0", "host.docker.internal"))
            / iot_path
        )
        client = build_client(self.documents_api_service)
        document_data = {
            "informatieobjecttype": str(iot_url),
            "bronorganisatie": "000000000",
            "creatiedatum": "2024-09-18",
            "titel": "Test document",
            "auteur": "Automated test suite",
            "taal": "ENG",
            "bestandsomvang": 0,
        }

        response = client.post("enkelvoudiginformatieobjecten", json=document_data)

        self.assertEqual(response.status_code, 201, response.json())

    def test_can_create_document_with_dummy_informatieobjecttype(self):
        iot_path = reverse(
            "catalogi-informatieobjecttypen-detail",
            kwargs={"uuid": DUMMY_IC_UUID},
        )
        iot_url = (
            furl(self.live_server_url.replace("0.0.0.0", "host.docker.internal"))
            / iot_path
        )
        client = build_client(self.documents_api_service)
        document_data = {
            "informatieobjecttype": str(iot_url),
            "bronorganisatie": "000000000",
            "creatiedatum": "2024-09-18",
            "titel": "Test document with dummy IC",
            "auteur": "Automated test suite",
            "taal": "ENG",
            "bestandsomvang": 0,
        }

        response = client.post("enkelvoudiginformatieobjecten", json=document_data)

        self.assertEqual(response.status_code, 201, response.json())
