from django.test import tag

from hypothesis import given, strategies as st
from hypothesis.extra.django import SimpleTestCase

from woo_publications.celery import sentry_exponential_backoff


class CeleryAppTests(SimpleTestCase):
    def test_can_import_module(self):
        try:
            from . import celery  # noqa
        except ImportError:
            self.fail("Could not import celery app module.")

    @tag("hypothesis")
    @given(
        base=st.integers(min_value=0, max_value=1000),
        cap=st.integers(min_value=0, max_value=1600),
        retries=st.integers(min_value=0, max_value=8),
    )
    def test_exponential_backoff(self, base: int, cap: int, retries: int):
        value = sentry_exponential_backoff(base=base, cap=cap, retries=retries)

        assert value == cap if base > cap else value >= base

        self.assertTrue(value <= cap)
