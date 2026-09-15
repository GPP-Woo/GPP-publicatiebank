import datetime

from django.urls import path

from rest_framework import serializers, status, views
from rest_framework.response import Response
from rest_framework.test import APITestCase, URLPatternsTestCase

from woo_publications.api.fields import WorkDateField


class TestCustomFieldsSerializer(serializers.Serializer):
    work_date_field = WorkDateField()


class TestCustomFieldsView(views.APIView):
    """
    A simple ViewSet that mimics retrieval, creation and updating of data
    to test the behavior of custom fields.
    """

    serializer_class = TestCustomFieldsSerializer
    authentication_classes = ()
    permission_classes = ()

    @property
    def get_default_data(self):
        return {"work_date_field": datetime.date(2025, 5, 25)}

    def get(self, request):
        serializer = self.serializer_class(instance=self.get_default_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_201_CREATED)

    def put(self, request, pk=None):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class ApiCustomFieldsTests(URLPatternsTestCase, APITestCase):
    urlpatterns = [
        path("custom_fields", TestCustomFieldsView.as_view()),
    ]

    def test_get_endpoint(self):
        response = self.client.get("/custom_fields")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"workDateField": "2025-05-25"})

    def test_create_endpoint(self):
        response = self.client.post(
            "/custom_fields", data={"workDateField": "2026-04-27"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {"workDateField": "2026-04-28"})

    def test_update_endpoint(self):
        response = self.client.put(
            "/custom_fields", data={"workDateField": "2026-04-27"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"workDateField": "2026-04-28"})
