import tempfile
from io import StringIO
from pathlib import Path
from uuid import uuid4

from django.core.management import call_command
from django.test import TestCase

import requests
import requests_mock

from woo_publications.utils.tests.vcr import VCRMixin

from ..models import Theme
from ..theme_sync import ThemeWaardenlijstError, update_theme


class UpdateThemeTestCase(VCRMixin, TestCase):
    def test_data_gets_stored_and_turned_into_fixture(self):
        assert not Theme.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            update_theme(file_path)

            with self.subTest("database populated"):
                self.assertEqual(Theme.objects.count(), 92)

            with self.subTest("user content does not cause conflicts"):
                theme = Theme.objects.order_by("pk").last()
                assert theme is not None

                theme.identifier = "https://something.else"
                theme.uuid = uuid4()
                theme.path = theme.path + "1"
                theme.save()

                call_command("loaddata", file_path, stdout=StringIO())

                self.assertEqual(Theme.objects.count(), 93)

    def test_data_update_existing_data(self):
        assert not Theme.objects.exists()

        root = Theme.add_root(
            identifier="https://identifier.overheid.nl/tooi/def/thes/top/c_0361ffb3",
            naam="temp-name-will-be-updated",
        )

        root_which_will_become_child = Theme.add_root(
            identifier="https://identifier.overheid.nl/tooi/def/thes/top/c_2408fb5a",
            naam="cultureel erfgoed",
        )

        child_with_incorrect_parent = root.add_child(
            identifier="https://identifier.overheid.nl/tooi/def/thes/top/c_068da9fb",
            naam="inkoop en beheer",
        )

        child_which_name_will_change = root.add_child(
            identifier="https://identifier.overheid.nl/tooi/def/thes/top/c_75809540",
            naam="name_that_will_be_updated",
        )

        child_not_updated_or_moved = root.add_child(
            identifier="https://identifier.overheid.nl/tooi/def/thes/top/c_e277e756",
            naam="religie",
        )

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            update_theme(file_path)

            with self.subTest("database hasn't added extra items."):
                self.assertEqual(Theme.objects.count(), 92)

            with self.subTest("root has updated back to original data"):
                root.refresh_from_db()

                self.assertNotEqual(root.naam, "temp-name-will-be-updated")

            with self.subTest("childs data doesn't change"):
                child_not_updated_or_moved.refresh_from_db()

                self.assertEqual(child_not_updated_or_moved.naam, "religie")

                self.assertEqual(child_not_updated_or_moved.get_root(), root)

            with self.subTest("child's name is updated"):
                child_which_name_will_change.refresh_from_db()

                self.assertNotEqual(
                    child_with_incorrect_parent.naam, "name_that_will_be_updated"
                )

                self.assertEqual(child_which_name_will_change.get_root(), root)

            with self.subTest("child's parent is updated"):
                child_with_incorrect_parent.refresh_from_db()

                self.assertEqual(child_with_incorrect_parent.naam, "inkoop en beheer")

                self.assertNotEqual(child_with_incorrect_parent.get_root(), root)

            with self.subTest("root gets moved to child"):
                root_which_will_become_child.refresh_from_db()

                self.assertEqual(root_which_will_become_child.naam, "cultureel erfgoed")

                self.assertEqual(root_which_will_become_child.get_root(), root)

    @requests_mock.Mocker()
    def test_request_get_raises_valid_exception(self, m):
        m.register_uri(
            requests_mock.ANY, requests_mock.ANY, exc=requests.RequestException
        )
        assert not Theme.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                ThemeWaardenlijstError,
                "Could not retrieve the value list data.",
            ):
                update_theme(file_path)

    @requests_mock.Mocker()
    def test_request_get_invalid_status_code(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=400)
        assert not Theme.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                ThemeWaardenlijstError,
                "Got an unexpected response status code when retrieving the value list "
                "data: 400.",
            ):
                update_theme(file_path)

    @requests_mock.Mocker()
    def test_request_has_no_data(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=200, json=[])
        assert not Theme.objects.exists()

        with tempfile.NamedTemporaryFile(suffix=".json") as file:
            file_path = Path(file.name)

            with self.assertRaisesMessage(
                ThemeWaardenlijstError,
                "Received empty data from value list.",
            ):
                update_theme(file_path)
