from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase


class APIschemaGenerationTests(APITestCase):
    def test_schema_endpoint(self):
        # kitchensink test - request the API schema which should process all (custom)
        # hooks and extensions
        with self.subTest("Test application API"):
            url = reverse("application:schema-json-application")

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.subTest("Test reuse API"):
            url = reverse("reuse:schema-json-reuse")

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
