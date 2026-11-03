from django.db import IntegrityError
from django.test import TestCase

from .factories import TokenAuthFactory


class ApplicationModelTestCase(TestCase):
    def test_unique_token(self):
        with self.assertRaisesMessage(
            IntegrityError,
            'duplicate key value violates unique constraint "unique_token"'
            "\nDETAIL:  Key (token)=(<TOKEN>) already exists.",
        ):
            TokenAuthFactory.create_batch(2, token="<TOKEN>")

    def test_allow_creating_multiple_objects_with_blank_token(self):
        TokenAuthFactory.create_batch(size=2)
