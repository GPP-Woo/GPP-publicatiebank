import tempfile
from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.core.management import call_command
from django.test import TestCase

import requests
import requests_mock

from woo_publications.utils.tests.vcr import VCRMixin

from ..models import Organisation
from ..organisation_sync import (
    MUNICIPALITY_WAARDENLIJST_URL,
    OrganisatieWaardenlijstError,
    update_organisation,
)
from .factories import OrganisationFactory


class UpdateOrganisationTestCase(VCRMixin, TestCase):
    def test_data_gets_stored_and_turned_into_fixture(self):
        assert not Organisation.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            update_organisation(file_path)

            with self.subTest("database populated"):
                self.assertEqual(Organisation.objects.count(), 1137)

            with self.subTest("user content does not cause conflicts"):
                organisation = Organisation.objects.order_by("pk").last()
                assert organisation is not None

                organisation.identifier = "https://something.else"
                organisation.uuid = uuid4()
                organisation.save()

                call_command("loaddata", file_path, stdout=StringIO())

                self.assertEqual(Organisation.objects.count(), 1138)

    def test_data_update_existing_data(self):
        assert not Organisation.objects.exists()

        organisation = OrganisationFactory.create(
            identifier="https://identifier.overheid.nl/tooi/id/gemeente/gm0003",
            naam="temp-name-will-be-updated",
        )

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            update_organisation(file_path)

            with self.subTest("database hasn't added extra items."):
                self.assertEqual(Organisation.objects.count(), 1137)

            with self.subTest("organisation has updated back to original data"):
                organisation.refresh_from_db()

                self.assertNotEqual(organisation.naam, "temp-name-will-be-updated")

    @requests_mock.Mocker()
    def test_request_get_raises_valid_exception(self, m):
        m.register_uri(
            requests_mock.ANY, requests_mock.ANY, exc=requests.RequestException
        )
        assert not Organisation.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                OrganisatieWaardenlijstError,
                "Could not retrieve the value list data from url "
                f"`{MUNICIPALITY_WAARDENLIJST_URL}`.",
            ):
                update_organisation(file_path)

    @requests_mock.Mocker()
    def test_request_get_invalid_status_code(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=400)
        assert not Organisation.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                OrganisatieWaardenlijstError,
                "Got an unexpected response status code when retrieving the value "
                f"list data from url `{MUNICIPALITY_WAARDENLIJST_URL}`: 400.",
            ):
                update_organisation(file_path)

    @requests_mock.Mocker()
    def test_request_has_no_data(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=200, json=[])
        assert not Organisation.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                OrganisatieWaardenlijstError,
                "Received empty data from value list "
                f"`{MUNICIPALITY_WAARDENLIJST_URL}`.",
            ):
                update_organisation(file_path)
