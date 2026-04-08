import io
from tempfile import NamedTemporaryFile

from django.test import TestCase

from woo_publications.publications.strip_rtf import StripRtf


class StripRTFParserTestCase(TestCase):
    def test_detect_tail_and_head(self):
        rtf_file = io.BytesIO(
            b"{\rtf1\ansi\deff0{\info{WOW INFO}}{\info{WOW More info???}}}"
        )

        with NamedTemporaryFile(suffix=".rtf") as temp:
            StripRtf(input_file=rtf_file, output_file=temp).strip_file()

            temp.seek(0)
            self.assertEqual(temp.read(), b"{\rtf1\x07nsi\\deff0{\\info}{\\info}}")

    def test_detect_new_lines(self):
        rtf_file = io.BytesIO(b"{\rtf1\ansi\deff0{\info{WOW INFO}}}")

        with NamedTemporaryFile(suffix=".rtf") as temp:
            StripRtf(input_file=rtf_file, output_file=temp).strip_file()

            temp.seek(0)
            self.assertEqual(temp.read(), b"{\rtf1\ansi\deff0{\info}}")
