from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from mozilla_django_oidc_db.constants import OIDC_ADMIN_CONFIG_IDENTIFIER
from mozilla_django_oidc_db.tests.factories import OIDCClientFactory
from mozilla_django_oidc_db.tests.mixins import OIDCMixin
from mozilla_django_oidc_db.tests.utils import keycloak_login

from woo_publications.utils.tests.vcr import VCRMixin

from ..models import User
from .factories import UserFactory


class OIDCLoginButtonTestCase(OIDCMixin, WebTest):
    def test_oidc_button_disabled(self):
        OIDCClientFactory.create(
            identifier=OIDC_ADMIN_CONFIG_IDENTIFIER,
            enabled=False,
            with_admin_options=True,
        )

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is not visible
        self.assertIsNone(oidc_login_link)

    def test_oidc_button_enabled(self):
        OIDCClientFactory.create(
            identifier=OIDC_ADMIN_CONFIG_IDENTIFIER,
            enabled=True,
            with_admin_options=True,
        )

        response = self.app.get(reverse("admin:login"))

        oidc_login_link = response.html.find(
            "a", string=_("Login with organization account")
        )

        # Verify that the login button is visible
        self.assertIsNotNone(oidc_login_link)
        self.assertEqual(
            oidc_login_link.attrs["href"], reverse("oidc_authentication_init")
        )


class OIDCFLowTests(VCRMixin, OIDCMixin, WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.oidc_client = OIDCClientFactory.create(
            identifier=OIDC_ADMIN_CONFIG_IDENTIFIER,
            enabled=True,
            with_admin_options=True,
            oidc_rp_client_id="testid",
            oidc_rp_client_secret="7DB3KUAAizYCcmZufpHRVOcD0TOkNO3I",
            oidc_rp_sign_algo="RS256",
            oidc_rp_scopes_list=["openid"],
            oidc_provider__oidc_op_discovery_endpoint=(
                "http://localhost:8080/realms/test/"
            ),
            # factory is broken
            oidc_provider__oidc_op_authorization_endpoint=(
                "http://localhost:8080/realms/test/protocol/openid-connect/auth"
            ),
        )
        cls.oidc_client.options["user_settings"]["claim_mappings"]["username"] = [
            "preferred_username"
        ]
        cls.oidc_client.save()

    def test_duplicate_email_unique_constraint_violated(self):
        # this user collides on the email address
        staff_user = UserFactory.create(
            is_staff=True, username="no-match", email="admin@example.com"
        )
        login_page = self.app.get(reverse("admin:login"))
        start_response = login_page.click(
            description=_("Login with organization account")
        )
        assert start_response.status_code == 302
        redirect_uri = keycloak_login(
            start_response["Location"], username="admin", password="admin"
        )

        error_page = self.app.get(redirect_uri, auto_follow=True)

        with self.subTest("error page"):
            self.assertEqual(error_page.status_code, 200)
            self.assertEqual(error_page.request.path, reverse("admin-oidc-error"))
            self.assertEqual(
                error_page.context["oidc_error"].strip(),
                'duplicate key value violates unique constraint "filled_email_unique"\n'
                "DETAIL:  Key (email)=(admin@example.com) already exists.",
            )
            self.assertContains(
                error_page, "duplicate key value violates unique constraint"
            )

        with self.subTest("user state unmodified"):
            self.assertEqual(User.objects.count(), 1)
            staff_user.refresh_from_db()
            self.assertEqual(staff_user.username, "no-match")
            self.assertEqual(staff_user.email, "admin@example.com")
            self.assertTrue(staff_user.is_staff)

    def test_happy_flow(self):
        login_page = self.app.get(reverse("admin:login"))
        start_response = login_page.click(
            description=_("Login with organization account")
        )
        assert start_response.status_code == 302
        redirect_uri = keycloak_login(
            start_response["Location"], username="admin", password="admin"
        )

        admin_index = self.app.get(redirect_uri, auto_follow=True)

        self.assertEqual(admin_index.status_code, 200)
        self.assertEqual(admin_index.request.path, reverse("admin:index"))

        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.username, "admin")

    def test_happy_flow_existing_user(self):
        self.oidc_client.options["groups_settings"]["make_users_staff"] = False
        self.oidc_client.save()

        staff_user = UserFactory.create(
            is_staff=True, username="admin", email="update-me"
        )
        login_page = self.app.get(reverse("admin:login"))
        start_response = login_page.click(
            description=_("Login with organization account")
        )
        assert start_response.status_code == 302
        redirect_uri = keycloak_login(
            start_response["Location"], username="admin", password="admin"
        )

        admin_index = self.app.get(redirect_uri, auto_follow=True)

        self.assertEqual(admin_index.status_code, 200)
        self.assertEqual(admin_index.request.path, reverse("admin:index"))

        self.assertEqual(User.objects.count(), 1)
        staff_user.refresh_from_db()
        self.assertEqual(staff_user.username, "admin")
        self.assertEqual(staff_user.email, "admin@example.com")
