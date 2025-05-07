from django.test import SimpleTestCase


class CeleryAppTests(SimpleTestCase):
    def test_can_import_module(self):
        try:
            from . import celery  # noqa
        except ImportError:
            self.fail("Could not import celery app module.")
