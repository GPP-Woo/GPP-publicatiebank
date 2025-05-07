from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

import requests_mock

from woo_publications.utils.tests.vcr import VCRMixin

from ..models import Theme


class TestUpdateThemeFromWaardenlijstCommand(VCRMixin, TestCase):
    @patch(
        "woo_publications.metadata.management.commands"
        ".update_theme_from_waardenlijst.update_theme",
    )
    def test_default_fixture_path(self, mock_update: MagicMock):
        call_command("update_theme_from_waardenlijst")

        mock_update.assert_called_once_with(
            settings.DJANGO_PROJECT_DIR / "fixtures" / "themes.json"
        )

    @patch(
        "woo_publications.metadata.management.commands"
        ".update_theme_from_waardenlijst.update_theme",
    )
    def test_command_with_file_path_flag(self, mock_update: MagicMock):
        call_command("update_theme_from_waardenlijst", file_path="/tmp/dummy.json")

        mock_update.assert_called_once_with(Path("/tmp/dummy.json"))

    @requests_mock.Mocker()
    def test_raise_command_error(self, m):
        m.register_uri(requests_mock.ANY, requests_mock.ANY, status_code=400)
        assert not Theme.objects.exists()

        with self.assertRaisesMessage(
            CommandError,
            "Got an unexpected response status code when retrieving the value list "
            "data: 400.",
        ):
            call_command("update_theme_from_waardenlijst")
