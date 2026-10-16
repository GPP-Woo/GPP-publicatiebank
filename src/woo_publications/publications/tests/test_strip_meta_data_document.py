import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.test.utils import override_settings

from parametrize import parametrize

from ..file_processing import (
    MetaDataStripError,
    strip_html,
    strip_ms_office_document,
    strip_open_document,
    strip_pdf,
)

METADATA_PDF = (
    Path(settings.DJANGO_PROJECT_DIR) / "publications" / "tests" / "files" / "amore.pdf"
)
NO_METADATA_PDF = (
    Path(settings.DJANGO_PROJECT_DIR)
    / "publications"
    / "tests"
    / "files"
    / "no_meta_data.pdf"
)


class StripMetaDataFunctionsRemoveTempFileOnErrorTests(SimpleTestCase):
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
class StripMetaDataFileSizeTooLargeTests(SimpleTestCase):
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


class StripPDFTests(SimpleTestCase):
    @parametrize(
        "pdf_path",
        [
            METADATA_PDF,
            NO_METADATA_PDF,
        ],
    )
    def test_strip_pdf_does_not_duplicate_objects(self, pdf_path):
        original = pdf_path.read_bytes()

        with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_file:
            temp_file.write(original)
            strip_pdf(temp_file)
            temp_file.seek(0)
            stripped = temp_file.read()

        self.assertLess(stripped.count(b" 0 obj"), original.count(b" 0 obj"))
        self.assertLess(len(stripped), len(original))

    def test_pdf_document_error(self):
        with tempfile.NamedTemporaryFile(suffix="txt") as temp_file:
            temp_file.write(b"hello world.")

            before_tmp_dir_state = os.listdir(tempfile.gettempdir())

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata of the PDF file.",
            ):
                strip_pdf(temp_file)

            self.assertEqual(before_tmp_dir_state, os.listdir(tempfile.gettempdir()))
