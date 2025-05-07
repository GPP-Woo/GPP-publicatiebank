from django.test import TestCase
from django.urls import reverse


class IndexTests(TestCase):
    def test_index_page_loads_without_errors(self):
        root_url = reverse("root")

        response = self.client.get(root_url)

        self.assertEqual(response.status_code, 200)
