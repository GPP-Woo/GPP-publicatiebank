import os
import tempfile

from django.test import TestCase

from ..file_processing import MetaDataStripError, strip_open_document


class StripOpenDocumentDocumentCleanupTestCase(TestCase):
    def test_none_zip_file(self):
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
