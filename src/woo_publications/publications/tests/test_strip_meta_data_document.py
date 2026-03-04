import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

from ..file_processing import (
    MetaDataStripError,
    strip_html,
    strip_ms_office_document,
    strip_open_document,
)


class StripMetaDataFunctionsRemoveTempFileOnErrorTests(TestCase):
    def test_open_document_strip_error(self):
        with tempfile.NamedTemporaryFile(suffix="txt") as temp_file:
            temp_file.write(b"hello world.")

            before_tmp_dir_state = os.listdir(tempfile.gettempdir())

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata "
                "of the open document file",
            ):
                strip_open_document(temp_file)

            self.assertEqual(before_tmp_dir_state, os.listdir(tempfile.gettempdir()))

    def test_ms_document_strip_error(self):
        with tempfile.NamedTemporaryFile(suffix="txt") as temp_file:
            temp_file.write(b"hello world.")

            before_tmp_dir_state = os.listdir(tempfile.gettempdir())

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata "
                "of the MS document file",
            ):
                strip_ms_office_document(temp_file)

            self.assertEqual(before_tmp_dir_state, os.listdir(tempfile.gettempdir()))


@override_settings(STRIP_METADATA_HTML_MAX_FILE_SIZE=1)
class StripMetaDataFileSizeTooLargeTests(TestCase):
    def test_strip_html_data(self):
        html_path = (
            Path(settings.DJANGO_PROJECT_DIR)
            / "publications"
            / "tests"
            / "files"
            / "test.html"
        )

        with (
            html_path.open("rb") as html_file,
            self.assertRaisesMessage(
                MetaDataStripError, "The file is to large for us to process."
            ),
        ):
            strip_html(html_file)
