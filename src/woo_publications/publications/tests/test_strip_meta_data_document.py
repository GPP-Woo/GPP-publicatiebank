from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

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
    strip_rtf_file,
    strip_zip_file,
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


class StripMetaDataFunctionsErrorTests(SimpleTestCase):
    def test_open_document_strip_error(self):
        with (
            NamedTemporaryFile(suffix=".txt") as temp_file,
            NamedTemporaryFile() as new_file,
        ):
            temp_file.write(b"hello world.")

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata "
                "of the open document file",
            ):
                strip_open_document(temp_file, new_file)

    def test_ms_document_strip_error(self):
        with (
            NamedTemporaryFile(suffix=".txt") as temp_file,
            NamedTemporaryFile() as new_file,
        ):
            temp_file.write(b"hello world.")

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata "
                "of the MS document file",
            ):
                strip_ms_office_document(temp_file, new_file)

    @patch(
        "woo_publications.publications.file_processing.RtfStreamFilter.process_chunk",
        side_effect=OSError(),
    )
    def test_rtf_document_strip_error(self, mock_process_chunk: MagicMock):
        with (
            NamedTemporaryFile(suffix=".rtf") as temp_file,
            NamedTemporaryFile() as new_file,
        ):
            temp_file.write(b"hello world.")

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata of the RTF file",
            ):
                strip_rtf_file(temp_file, new_file)

    def test_pdf_document_error(self):
        with (
            NamedTemporaryFile(suffix=".pdf") as temp_file,
            NamedTemporaryFile() as new_file,
        ):
            temp_file.write(b"hello world.")

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata of the PDF file",
            ):
                strip_pdf(temp_file, new_file)

    def test_zip_document_error(self):
        with (
            NamedTemporaryFile(suffix=".text") as temp_file,
            NamedTemporaryFile() as new_file,
        ):
            temp_file.write(b"hello world.")

            with self.assertRaisesMessage(
                MetaDataStripError,
                "Something went wrong while stripping the metadata of the ZIP file",
            ):
                strip_zip_file(temp_file, new_file)


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
            html_path.open("rb") as temp_file,
            NamedTemporaryFile() as new_file,
            self.assertRaisesMessage(
                MetaDataStripError, "The file is to large for us to process."
            ),
        ):
            strip_html(temp_file, new_file)


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

        with (
            pdf_path.open("rb") as in_file,
            NamedTemporaryFile() as new_file,
        ):
            strip_pdf(in_file, new_file)
            new_file.seek(0)
            stripped = new_file.read()

        self.assertLessEqual(stripped.count(b" 0 obj"), original.count(b" 0 obj"))
        self.assertLessEqual(len(stripped), len(original))
