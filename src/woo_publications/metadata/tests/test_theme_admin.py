from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory

from .factories import ThemeFactory


@disable_admin_mfa()
class TestInformationCategoryAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_theme_admin_show_items(self):
        ThemeFactory.create(naam="first item")
        ThemeFactory.create(naam="second item")

        response = self.app.get(
            reverse(
                "admin:metadata_theme_changelist",
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        # test the amount of rows present
        self.assertContains(response, "field-identifier", 2)

    def test_theme_admin_search(self):
        theme = ThemeFactory.create(naam="first item")
        theme2 = ThemeFactory.create(naam="second item")

        response = self.app.get(
            reverse(
                "admin:metadata_theme_changelist",
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter on naam"):
            form["q"] = "first item"

            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, theme.identifier, 1)

        with self.subTest("filter on identifier"):
            form["q"] = theme2.identifier

            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, "second item", 1)

    def test_theme_admin_can_not_update(
        self,
    ):
        theme = ThemeFactory.create(naam="first item")
        url = reverse(
            "admin:metadata_theme_change",
            kwargs={"object_id": theme.id},
        )

        response = self.app.get(url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["theme_form"]

        self.assertNotIn("naam", form.fields)
        self.assertNotIn("identifier", form.fields)

        response = form.submit(name="_save", expect_errors=True)

        self.assertEqual(response.status_code, 403)

    def test_theme_admin_can_not_create(
        self,
    ):
        url = reverse("admin:metadata_theme_add")

        response = self.app.get(url, user=self.user, expect_errors=True)

        self.assertEqual(response.status_code, 403)
