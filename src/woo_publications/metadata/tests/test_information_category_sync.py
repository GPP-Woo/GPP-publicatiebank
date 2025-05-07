import tempfile
from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.core.management import call_command
from django.test import TestCase

import requests
import requests_mock

from woo_publications.utils.tests.vcr import VCRMixin

from ..information_category_sync import (
    InformatieCategoryWaardenlijstError,
    update_information_category,
)
from ..models import InformationCategory


class UpdateInformatieCategoryTestCase(VCRMixin, TestCase):
    def test_data_gets_stored_and_turned_into_fixture(self):
        assert not InformationCategory.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            update_information_category(file_path)

            with self.subTest("database populated"):
                self.assertEqual(InformationCategory.objects.count(), 18)

            with self.subTest("user content does not cause conflicts"):
                information_category = InformationCategory.objects.order_by("pk").last()
                assert information_category is not None

                information_category.identifier = "https://something.else"
                information_category.uuid = uuid4()
                information_category.save()

                call_command("loaddata", file_path, stdout=StringIO())

                self.assertEqual(InformationCategory.objects.count(), 19)

    @requests_mock.Mocker()
    def test_request_get_raises_valid_exception(self, m):
        m.register_uri(
            requests_mock.ANY, requests_mock.ANY, exc=requests.RequestException
        )
        assert not InformationCategory.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                InformatieCategoryWaardenlijstError,
                "Could not retrieve the value list data.",
            ):
                update_information_category(file_path)

    @requests_mock.Mocker()
    def test_request_get_invalid_status_code(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=400)
        assert not InformationCategory.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                InformatieCategoryWaardenlijstError,
                "Got an unexpected response status code when retrieving the value list "
                "data: 400.",
            ):
                update_information_category(file_path)

    @requests_mock.Mocker()
    def test_request_has_no_data(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=200, json=[])
        assert not InformationCategory.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                InformatieCategoryWaardenlijstError,
                "Received empty data from value list.",
            ):
                update_information_category(file_path)
