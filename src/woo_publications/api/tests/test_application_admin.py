import datetime

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from django_webtest import WebTest
from furl import furl
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory

from ..models import Application
from .factories import TokenAuthFactory


@disable_admin_mfa()
class ApplicationAdminTest(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_list_view_does_not_show_token(self):
        application_1 = TokenAuthFactory.create()
        application_2 = TokenAuthFactory.create(expire_date=datetime.date(1970, 1, 1))
        response = self.app.get(
            reverse(
                "admin:api_application_changelist",
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        # test the amount of rows present
        self.assertContains(response, "field-active", 2)
        self.assertNotContains(response, application_1.raw_token)
        self.assertNotContains(response, application_1.token)
        self.assertNotContains(response, application_2.raw_token)
        self.assertNotContains(response, application_2.token)
        self.assertContains(response, "/static/admin/img/icon-yes.svg", 1)
        self.assertContains(response, "/static/admin/img/icon-no.svg", 1)

    @override_settings(LANGUAGE_CODE="nl")
    def test_detail_view_does_not_show_token(self):
        application = TokenAuthFactory.create(viewed_token_at=timezone.now())
        response = self.app.get(
            reverse(
                "admin:api_application_change",
                kwargs={"object_id": application.pk},
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["application_form"]
        form["api_access"].force_value([])
        form["initial-permissions"].force_value([])
        form["permissions"].force_value([])
        form_fields = [field for field in form.fields.keys()]

        # assert that on the edit page all buttons are visible
        self.assertIn("_save", form_fields)
        self.assertIn("_addanother", form_fields)
        self.assertIn("_continue", form_fields)
        self.assertContains(response, "Opslaan")
        self.assertContains(response, "Opslaan en nieuwe toevoegen")
        self.assertContains(response, "Opslaan en opnieuw bewerken")
        # assert token not on page
        self.assertNotIn("token", form_fields)
        self.assertNotContains(response, application.raw_token)
        self.assertNotContains(response, application.token)

        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        # ensure that during update user doesn't get redirected to token page.
        self.assertEqual(
            response.url,
            reverse("admin:api_application_changelist"),
        )

    @override_settings(LANGUAGE_CODE="nl")
    def test_create_token(self):
        assert Application.objects.count() == 0
        response = self.app.get(reverse("admin:api_application_add"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.forms["application_form"]
        form["api_access"].force_value([])
        form["permissions"].force_value([])
        form["initial-permissions"].force_value([])
        form["contact_person"] = "some user"
        form["email"] = "some@user.email"
        form["phone_number"] = "07700900999"

        form_fields = [field for field in form.fields.keys()]

        # assert that on the edit page all buttons are visible
        self.assertIn("_save", form_fields)
        self.assertNotIn("_addanother", form_fields)
        self.assertNotIn("_continue", form_fields)
        self.assertNotContains(response, "Opslaan en nieuwe toevoegen")
        self.assertNotContains(response, "Opslaan en opnieuw bewerken")
        # assert token not on page
        self.assertNotIn("token", form_fields)
        self.assertNotContains(response, "Token")

        response = form.submit(name="_save")

        application = Application.objects.get()

        self.assertEqual(response.status_code, 302)
        # ensure that during creation user gets redirected to token page.
        self.assertEqual(
            response.url,
            reverse("admin:token_view", kwargs={"object_id": application.pk}),
        )


@disable_admin_mfa()
class ApplicationTokenAdminTests(WebTest):
    def test_staff_user_required(self):
        application = TokenAuthFactory.create()
        bad_users = (
            None,
            UserFactory.create(),
        )
        url = reverse("admin:token_view", kwargs={"object_id": application.pk})

        for user in bad_users:
            self.client.logout()
            if user is not None:
                self.client.force_login(user)

            response = self.client.get(url)

            self.assertRedirects(
                response,
                str(furl(reverse("admin:login")).add({"next": url})),
            )

    def test_access_blocked_without_permissions(self):
        staff_user_without_permissions = UserFactory.create(is_staff=True)
        application = TokenAuthFactory.create()
        url = reverse("admin:token_view", kwargs={"object_id": application.pk})
        self.client.force_login(staff_user_without_permissions)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_token_already_seen(self):
        user = UserFactory.create(superuser=True)
        application = TokenAuthFactory.create(viewed_token_at=timezone.now())
        url = reverse("admin:token_view", kwargs={"object_id": application.pk})

        response = self.app.get(url, user=user, expect_errors=True)

        self.assertEqual(response.status_code, 404)

    def test_token_shown_on_screen(self):
        user = UserFactory.create(superuser=True)
        application = Application.objects.create()
        url = reverse("admin:token_view", kwargs={"object_id": application.pk})

        self.assertFalse(application.token)

        response = self.app.get(url, user=user)

        self.assertEqual(response.status_code, 200)
        application.refresh_from_db()
        self.assertTrue(application.token)
