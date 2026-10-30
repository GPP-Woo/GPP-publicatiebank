from django.urls import path

from rest_framework import generics, serializers, status
from rest_framework.test import APITestCase, URLPatternsTestCase

from woo_publications.metadata.models import Organisation
from woo_publications.metadata.tests.factories import OrganisationFactory

from ..pagination import CursorPagination, DynamicPageSizePagination

EXPECTED_PAGE_SIZE = 10
EXPECTED_MAX_PAGE_SIZE = 100


class TestPaginationSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore
        model = Organisation
        fields = ("uuid",)


class TestDynamicPageSizePaginationViewSet(generics.ListAPIView):
    queryset = Organisation.objects.all().order_by("pk")
    serializer_class = TestPaginationSerializer
    pagination_class = DynamicPageSizePagination
    authentication_classes = ()
    permission_classes = ()

    """
    A simple ViewSet for listing or retrieving users.
    """


class TestCurserPaginationViewSet(generics.ListAPIView):
    queryset = Organisation.objects.all().order_by("pk")
    serializer_class = TestPaginationSerializer
    pagination_class = CursorPagination
    pagination_ordering = "-pk"
    authentication_classes = ()
    permission_classes = ()

    """
    A simple ViewSet for listing or retrieving users.
    """


class DynamicPageSizePaginationTest(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("pagination", TestDynamicPageSizePaginationViewSet.as_view()),
    ]

    def test_get_default_pagination(self):
        OrganisationFactory.create_batch(10)
        response = self.client.get("/pagination")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 10)
        self.assertEqual(len(data["results"]), EXPECTED_PAGE_SIZE)
        self.assertIsNone(data["next"])
        self.assertIsNone(data["previous"])

    def test_alter_page_size(self):
        OrganisationFactory.create_batch(15)

        with self.subTest("no page defined"):
            response = self.client.get("/pagination", {"pageSize": 5})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 15)
            self.assertEqual(len(data["results"]), 5)
            self.assertTrue(data["next"])
            self.assertIsNone(data["previous"])

        with self.subTest("page 1"):
            response = self.client.get("/pagination", {"pageSize": 5, "page": 1})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 15)
            self.assertEqual(len(data["results"]), 5)
            self.assertTrue(data["next"])
            self.assertIsNone(data["previous"])

        with self.subTest("page 2"):
            response = self.client.get("/pagination", {"pageSize": 5, "page": 2})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 15)
            self.assertEqual(len(data["results"]), 5)
            self.assertTrue(data["next"])
            self.assertTrue(data["previous"])

        with self.subTest("page 3"):
            response = self.client.get("/pagination", {"pageSize": 5, "page": 3})

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 15)
            self.assertEqual(len(data["results"]), 5)
            self.assertIsNone(data["next"])
            self.assertTrue(data["previous"])

    def test_page_size_succeed_max_size(self):
        over_max_size = EXPECTED_MAX_PAGE_SIZE + 1
        OrganisationFactory.create_batch(over_max_size)

        response = self.client.get("/pagination", {"pageSize": over_max_size})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], over_max_size)
        self.assertEqual(len(data["results"]), EXPECTED_MAX_PAGE_SIZE)


class CurserPaginationTest(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("pagination", TestCurserPaginationViewSet.as_view()),
    ]

    def test_get_default_pagination(self):
        OrganisationFactory.create_batch(10)
        response = self.client.get("/pagination")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["results"]), 10)
        self.assertIsNone(data["next"])
        self.assertIsNone(data["previous"])

    def test_with_next_and_previous(self):
        OrganisationFactory.create_batch(250)
        response = self.client.get("/pagination")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(response.json()["next"])

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data["results"]), 100)
        self.assertIsNotNone(data["next"])
        self.assertIsNotNone(data["previous"])
