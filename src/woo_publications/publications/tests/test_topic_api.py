import tempfile
from uuid import uuid4

from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.tests.mixins import (
    APIKeyUnAuthorizedMixin,
    APITestCaseMixin,
    TokenAuthMixin,
)

from ..constants import PublicationStatusOptions
from .factories import PublicationFactory, TopicFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class TopicApiAuthorizationAndPermissionTests(APIKeyUnAuthorizedMixin, APITestCase):
    def test_403_when_audit_headers_are_missing(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        list_endpoint = reverse("api:topic-list")
        detail_endpoint = reverse("api:topic-detail", kwargs={"uuid": str(uuid4())})

        with self.subTest(action="list"):
            response = self.client.get(list_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest(action="retrieve"):
            response = self.client.get(detail_endpoint, headers={})

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_api_key_result_in_401_with_wrong_credentials(self):
        topic = TopicFactory.create()
        list_url = reverse("api:topic-list")
        detail_url = reverse(
            "api:topic-detail",
            kwargs={"uuid": str(topic.uuid)},
        )

        # read
        self.assertWrongApiKeyProhibitsGetEndpointAccess(list_url)
        self.assertWrongApiKeyProhibitsGetEndpointAccess(detail_url)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TopicApiTestsCase(TokenAuthMixin, APITestCaseMixin, APITestCase):
    def test_list_topics(self):
        with freeze_time("2024-09-25T12:00:00-00:00"):
            topic = TopicFactory.create(
                officiele_titel="title one",
                omschrijving="bla bla bla",
                publicatiestatus=PublicationStatusOptions.published,
                promoot=True,
            )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic2 = TopicFactory.create(
                officiele_titel="title two",
                omschrijving="description",
                publicatiestatus=PublicationStatusOptions.revoked,
                promoot=False,
            )

        publication = PublicationFactory.create(onderwerpen=[topic])
        publication2 = PublicationFactory.create(onderwerpen=[topic2])

        response = self.client.get(reverse("api:topic-list"), headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

        with self.subTest("first_item_in_response_with_expected_data"):
            expected_first_topic_data = {
                "uuid": str(topic.uuid),
                "afbeelding": f"http://testserver{topic.afbeelding.url}",
                "publicaties": [str(publication.uuid)],
                "officieleTitel": "title one",
                "omschrijving": "bla bla bla",
                "publicatiestatus": PublicationStatusOptions.published,
                "promoot": True,
                "registratiedatum": "2024-09-25T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-25T14:00:00+02:00",
            }

            self.assertEqual(data["results"][0], expected_first_topic_data)

        with self.subTest("second_item_in_response_with_expected_data"):
            expected_second_topic_data = {
                "uuid": str(topic2.uuid),
                "afbeelding": f"http://testserver{topic2.afbeelding.url}",
                "publicaties": [str(publication2.uuid)],
                "officieleTitel": "title two",
                "omschrijving": "description",
                "publicatiestatus": PublicationStatusOptions.revoked,
                "promoot": False,
                "registratiedatum": "2024-09-24T14:00:00+02:00",
                "laatstGewijzigdDatum": "2024-09-24T14:00:00+02:00",
            }
            self.assertEqual(data["results"][1], expected_second_topic_data)

    def test_list_topic_filter_publications(self):
        topic, topic2, topic3, topic4 = TopicFactory.create_batch(4)

        publication = PublicationFactory.create(onderwerpen=[topic])
        publication2 = PublicationFactory.create(onderwerpen=[topic2])
        publication3 = PublicationFactory.create(onderwerpen=[topic3, topic4])

        list_url = reverse("api:topic-list")

        with self.subTest("filter on a single publication"):
            response = self.client.get(
                list_url,
                {"publicaties": str(publication.uuid)},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertItemInResults(data["results"], "uuid", str(topic.uuid), 1)

        with self.subTest("filter on multiple publicaties"):
            response = self.client.get(
                list_url,
                {"publicaties": f"{publication2.uuid},{publication3.uuid}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 3)
            self.assertItemInResults(data["results"], "uuid", str(topic2.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(topic3.uuid), 1)
            self.assertItemInResults(data["results"], "uuid", str(topic4.uuid), 1)

        with self.subTest("filter with invalid uuid"):
            fake_publication = uuid4()
            response = self.client.get(
                list_url,
                {"publicaties": f"{fake_publication}"},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            data = response.json()
            error_message = _(
                "Select a valid choice. %(value)s is not one of the available choices."
            ) % {"value": str(fake_publication)}

            self.assertEqual(data["publicaties"], [error_message])

    def test_list_topic_filter_publicatiestatus(self):
        published = TopicFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        concept = TopicFactory.create(publicatiestatus=PublicationStatusOptions.concept)
        revoked = TopicFactory.create(publicatiestatus=PublicationStatusOptions.revoked)
        list_url = reverse("api:topic-list")

        with self.subTest("filter on published topics"):
            response = self.client.get(
                list_url,
                {"publicatiestatus": PublicationStatusOptions.published},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(published.uuid))

        with self.subTest("filter on concept topics"):
            response = self.client.get(
                list_url,
                {"publicatiestatus": PublicationStatusOptions.concept},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(concept.uuid))

        with self.subTest("filter on revoked topics"):
            response = self.client.get(
                list_url,
                {"publicatiestatus": PublicationStatusOptions.revoked},
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["uuid"], str(revoked.uuid))

        with self.subTest("filter on multiple status choices"):
            response = self.client.get(
                list_url,
                {
                    "publicatiestatus": ",".join(
                        (
                            PublicationStatusOptions.published,
                            PublicationStatusOptions.revoked,
                        )
                    ),
                },
                headers=AUDIT_HEADERS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()

            self.assertEqual(data["count"], 2)
            self.assertItemInResults(data["results"], "uuid", str(published.uuid))
            self.assertItemInResults(data["results"], "uuid", str(revoked.uuid))
