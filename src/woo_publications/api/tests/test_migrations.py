from django.test import override_settings

from django_test_migrations.contrib.unittest_case import MigratorTestCase
from rest_framework.exceptions import AuthenticationFailed

from ..authorization import TokenAuthentication
from ..constants import PermissionOptions
from ..models import generate_token


class HashTokenMigrationTest(MigratorTestCase):
    migrate_from = ("api", "0005_application_viewed_token_at")
    migrate_to = ("api", "0006_alter_application_token")

    def prepare(self):
        Application = self.old_state.apps.get_model("api", "application")

        for _ in range(3):
            Application.objects.create(
                permissions=[PermissionOptions.read, PermissionOptions.write]
            )

        tokens = []

        for application in Application.objects.all():
            application.token = generate_token()
            tokens.append(application.token)
            application.save()

        self.tokens = tokens

    @override_settings(LANGUAGE_CODE="en")
    def test_0005_alter_application_token(self):
        Application = self.new_state.apps.get_model("api", "application")
        auth = TokenAuthentication()

        # check that database values doesn't pass the API token authentication
        for application in Application.objects.all():
            with self.assertRaisesMessage(AuthenticationFailed, "Invalid token"):
                auth.authenticate_credentials(application.token)

        # check that raw pre-existing tokens pass the token authentication
        for token in self.tokens:
            authenticate = auth.authenticate_credentials(token)
            self.assertTrue(Application.objects.get(pk=authenticate[1].pk))
