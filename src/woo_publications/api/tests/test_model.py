from django.db import IntegrityError
from django.test import TestCase

from ..models import Application


class ApplicationModelTestCase(TestCase):
    def test_unique_token(self):
        Application.objects.create(token="<TOKEN>")

        with self.assertRaisesMessage(
            IntegrityError,
            'duplicate key value violates unique constraint "unique_token"'
            "\nDETAIL:  Key (token)=(<TOKEN>) already exists.",
        ):
            Application.objects.create(token="<TOKEN>")

    def test_allow_creating_multiple_objects_with_blank_token(self):
        Application.objects.create()
        Application.objects.create()
