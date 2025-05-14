from django.test import tag
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from .factories import UserFactory


@disable_admin_mfa()
class UserAdminTests(WebTest):
    @tag("gh-81")
    def test_can_set_user_permissions(self):
        superuser = UserFactory.create(superuser=True)
        other_user = UserFactory.create()
        change_page = self.app.get(
            reverse("admin:accounts_user_change", args=(other_user.pk,)),
            user=superuser,
        )
        change_form = change_page.forms["user_form"]
        change_form["user_permissions"].select_multiple(
            texts=["Accounts | gebruiker | Can add user"]
        )

        response = change_form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
