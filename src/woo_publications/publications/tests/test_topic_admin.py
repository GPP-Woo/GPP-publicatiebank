from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory

from ..constants import PublicationStatusOptions
from ..models import Topic
from .factories import PublicationFactory, TopicFactory


@disable_admin_mfa()
class TestTopicAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_topic_admin_shows_items(self):
        TopicFactory.create(
            officiele_titel="title one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        TopicFactory.create(
            officiele_titel="title two",
            omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
        )
        response = self.app.get(
            reverse("admin:publications_topic_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-uuid", 2)

    def test_topic_admin_search(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic = TopicFactory.create(
                officiele_titel="title one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            topic2 = TopicFactory.create(
                officiele_titel="title two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
            )
        PublicationFactory.create(onderwerpen=[topic])
        publication2 = PublicationFactory.create(onderwerpen=[topic2])
        reverse_url = reverse("admin:publications_topic_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter on uuid"):
            form["q"] = str(topic2.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)

        with self.subTest("filter on publication uuid"):
            form["q"] = str(publication2.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(topic2.uuid), 1)

        with self.subTest("filter on officiele title"):
            form["q"] = "title one"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(topic.uuid), 1)

    def test_topic_admin_list_filter(self):
        self.app.set_user(user=self.user)

        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic = TopicFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                promoot=True,
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            topic2 = TopicFactory.create(
                publicatiestatus=PublicationStatusOptions.revoked,
                officiele_titel="title two",
                promoot=False,
            )
        reverse_url = reverse("admin:publications_topic_changelist")

        with freeze_time("2024-09-25T00:14:00-00:00"):
            response = self.app.get(reverse_url)

        self.assertEqual(response.status_code, 200)

        with self.subTest("filter on registratiedatum"):
            search_response = response.click(description=_("Today"), index=0)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on registratiedatum
            self.assertIn(
                "registratiedatum", search_response.request.environ["QUERY_STRING"]
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(topic2.uuid), 1)

        with self.subTest("filter on publicatiestatus"):
            search_response = response.click(
                description=str(PublicationStatusOptions.published.label)
            )

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(topic.uuid), 1)

        with self.subTest("filter on promoot"):
            search_response = response.click(description=_("Yes"), index=0)

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(topic.uuid), 1)

    @freeze_time("2024-09-25T00:14:00-00:00")
    def test_topic_admin_create(self):
        reverse_url = reverse("admin:publications_topic_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["topic_form"]

        with self.subTest("Cannot create a revoked topic"):
            form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"],
                None,
                _("You cannot create a {revoked} topic.").format(
                    revoked=PublicationStatusOptions.revoked.label.lower()
                ),
            )

        with self.subTest("complete data creates topic"):
            form["officiele_titel"] = "Lorem Ipsum"
            form["omschrijving"] = (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
            )
            form["publicatiestatus"] = PublicationStatusOptions.published
            form["promoot"] = False
            form.submit(name="_save")

            added_item = Topic.objects.order_by("-pk").first()
            assert added_item is not None
            self.assertEqual(added_item.officiele_titel, "Lorem Ipsum")
            self.assertEqual(
                added_item.omschrijving,
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
            self.assertEqual(
                added_item.publicatiestatus, PublicationStatusOptions.published
            )
            self.assertFalse(added_item.promoot)
            self.assertEqual(
                str(added_item.registratiedatum), "2024-09-25 00:14:00+00:00"
            )
            self.assertEqual(
                str(added_item.laatst_gewijzigd_datum), "2024-09-25 00:14:00+00:00"
            )

    def test_topic_admin_update(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic = TopicFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
            )

        reverse_url = reverse(
            "admin:publications_topic_change",
            kwargs={"object_id": topic.pk},
        )
        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["topic_form"]
        form["officiele_titel"] = "changed official title"
        form["omschrijving"] = "changed description"
        form["publicatiestatus"] = PublicationStatusOptions.revoked
        form["promoot"] = True

        with freeze_time("2024-09-27T12:00:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        topic.refresh_from_db()
        self.assertEqual(topic.officiele_titel, "changed official title")
        self.assertEqual(topic.omschrijving, "changed description")
        self.assertEqual(topic.publicatiestatus, PublicationStatusOptions.revoked)
        self.assertTrue(topic.promoot)
        self.assertEqual(str(topic.registratiedatum), "2024-09-24 12:00:00+00:00")
        self.assertEqual(str(topic.laatst_gewijzigd_datum), "2024-09-27 12:00:00+00:00")

    def test_topic_admin_delete(self):
        topic = TopicFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="title one",
        )
        reverse_url = reverse(
            "admin:publications_topic_delete",
            kwargs={"object_id": topic.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Topic.objects.filter(uuid=topic.uuid).exists())

    def test_topic_inline_publications_show(self):
        topic = TopicFactory.create()
        PublicationFactory.create(
            officiele_titel="title one",
        )
        PublicationFactory.create(
            onderwerpen=[topic],
            officiele_titel="title two",
        )

        reverse_url = reverse(
            "admin:publications_topic_change",
            kwargs={"object_id": topic.pk},
        )
        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "title one", 0)
        self.assertContains(response, "title two", 1)
