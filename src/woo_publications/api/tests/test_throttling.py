from django.test import SimpleTestCase
from django.urls import path

from freezegun import freeze_time
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.test import (
    APIRequestFactory,
    APITestCase,
    URLPatternsTestCase,
)

from woo_publications.api.reuse_api.urls import router

from ..authorization import TokenAuthentication
from ..throttling import AnonRateThrottle, ReuseRateThrottle
from .factories import TokenAuthFactory

request_factory = APIRequestFactory()


class LowAnonThrottleRateClass(AnonRateThrottle):
    # overwriting the AnonRateThrottle's THROTTLE_RATES since
    # @patch and @overwrite_settings both doesn't seem to work
    THROTTLE_RATES = {
        "anon": "1/day",
    }


class LowReuseThrottleRateClass(ReuseRateThrottle):
    # overwriting the ReuseRateThrottle's THROTTLE_RATES since
    # @patch and @overwrite_settings both doesn't seem to work
    THROTTLE_RATES = {
        "reuse": "2/day",
    }


class TestThrottlingView(views.APIView):
    throttle_classes = (
        LowAnonThrottleRateClass,
        LowReuseThrottleRateClass,
    )
    authentication_classes = (TokenAuthentication,)
    permission_classes = ()

    def get(self, request):
        return Response(status=status.HTTP_200_OK)


class TestNoThrottlingView(views.APIView):
    throttle_classes = ()
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        return Response(status=status.HTTP_200_OK)


class ThrottlingTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("throttling", TestThrottlingView.as_view()),
        path("brrr", TestNoThrottlingView.as_view()),
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.token_1 = TokenAuthFactory.create(
            read_write_permission=True, full_api_access=True
        ).raw_token

        cls.token_2 = TokenAuthFactory.create(
            read_write_permission=True, full_api_access=True
        ).raw_token

    def test_throttling_class(self):
        with freeze_time("2026-01-01T12:00:00-00:00"):
            for token in [self.token_1, self.token_2]:
                with self.subTest(
                    "Reuse Throttling only works twice a day", token=token
                ):
                    for _ in range(0, 2):
                        response = self.client.get(
                            "/throttling",
                            headers={"Authorization": f"Token {token}"},
                        )
                        self.assertEqual(response.status_code, status.HTTP_200_OK)

                    # third request gets denied
                    response = self.client.get(
                        "/throttling",
                        headers={"Authorization": f"Token {token}"},
                    )
                    self.assertEqual(
                        response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
                    )

            with self.subTest("Anon Throttling works once a day"):
                response = self.client.get("/throttling")
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                # second request gets denied
                response = self.client.get("/throttling")
                self.assertEqual(
                    response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
                )

            with self.subTest(
                "Api endpoint without throttling doesn't get impeded by throttling."
            ):
                # other api is not bound by throttling
                for _ in range(0, 3):
                    response = self.client.get("/brrr")
                    self.assertEqual(response.status_code, status.HTTP_200_OK)

        with (
            self.subTest("next day throttling resets"),
            freeze_time("2026-01-02T12:00:00-00:00"),
        ):
            for token in [self.token_1, self.token_2]:
                response = self.client.get(
                    "/throttling",
                    headers={"Authorization": f"Token {token}"},
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get("/throttling")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get("/brrr")
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class ReuseAPIThrottlingTests(SimpleTestCase):
    def test_throttling_classes_configured(self):
        viewsets: set = set()

        for url_patterns in router.urls:
            viewset = url_patterns.callback.cls  # pyright: ignore
            # ensures that we won't track viewsets and such from libaries like DRF
            if viewset.__module__.startswith("woo_publications"):
                viewsets.add(viewset)

        for viewset in viewsets:
            with self.subTest(viewset=viewset.__name__):
                throttling_classes = viewset.throttle_classes
                # check to see if the Anon and Reuse throttling classes are registered.
                self.assertIn(AnonRateThrottle, throttling_classes)
                self.assertIn(ReuseRateThrottle, throttling_classes)
