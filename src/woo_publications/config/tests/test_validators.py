from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from ..validators import validate_rsin


class RSINValidatorTests(SimpleTestCase):
    def test_valid_rsin(self):
        try:
            validate_rsin("123456782")
        except ValidationError as exc:
            raise self.failureException("Should have passed") from exc

    def test_values_wrong_length(self):
        with self.assertRaises(ValidationError) as exc_context:
            validate_rsin("12345678")

            self.assertEqual(exc_context.exception.code, "invalid-length")

        with self.assertRaises(ValidationError) as exc_context:
            validate_rsin("1234567822")

            self.assertEqual(exc_context.exception.code, "invalid-length")

    def test_not_numeric(self):
        with self.assertRaises(ValidationError):
            validate_rsin("12345678a")

    def test_elfproef(self):
        with self.assertRaises(ValidationError):
            validate_rsin("123456788")
