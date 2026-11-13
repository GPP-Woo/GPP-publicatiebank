import datetime

from django.urls import reverse
from django.utils import timezone

from django_webtest import WebTest
from freezegun.api import freeze_time
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.logging.models import TimelineLogProxy

from ...logging.constants import Events
from ..models import Application
from .factories import TokenAuthFactory


@disable_admin_mfa()
class ApplicationAuditLogAdminTest(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_detail_log(self):
        assert not TimelineLogProxy.objects.exists()

        with freeze_time("2026-11-11T11:11:11-00:00"):
            application = TokenAuthFactory.create(
                contact_person="Carson Pace",
                email="carson.pace@callousdaoboys.com",
                phone_number="0123456789",
                expire_date=datetime.date(2030, 1, 1),
                viewed_token_at=timezone.now(),
                read_write_permission=True,
            )

        response = self.app.get(
            reverse(
                "admin:api_application_change",
                kwargs={"object_id": application.pk},
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.read,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "_cached_object_repr": f"Application object ({application.pk})",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_create_token(self):
        assert not TimelineLogProxy.objects.exists()

        response = self.app.get(reverse("admin:api_application_add"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.forms["application_form"]
        form["api_access"].force_value([])
        form["permissions"].force_value([])
        form["initial-permissions"].force_value([])
        form["contact_person"] = "Maddie Caffrey"
        form["email"] = "maddie.caffrey@callousdaoboys.com"
        form["phone_number"] = "0123456789"
        form["expire_date"] = "2030-01-01"

        with freeze_time("2026-11-11T11:11:11-00:00"):
            response = form.submit(name="_save").follow()

        application = Application.objects.get()

        self.assertEqual(response.status_code, 200)

        self.assertEqual(TimelineLogProxy.objects.count(), 2)
        create_log, read_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("update audit logging"):
            expected_data = {
                "event": Events.create,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": application.pk,
                    "email": "maddie.caffrey@callousdaoboys.com",
                    "created": "2026-11-11T11:11:11Z",
                    "expire_date": "2030-01-01",
                    "permissions": [],
                    "api_access": [],
                    "phone_number": "0123456789",
                    "last_modified": "2026-11-11T11:11:11Z",
                    "contact_person": "Maddie Caffrey",
                    "viewed_token_at": None,
                },
                "_cached_object_repr": f"Application object ({application.pk})",
            }
            self.assertEqual(create_log.extra_data, expected_data)

        with self.subTest("read token audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": f"Application object ({application.pk})",
            }

            self.assertEqual(read_log.extra_data, expected_data)

    def test_update_token(self):
        assert not TimelineLogProxy.objects.exists()

        with freeze_time("2025-11-11T11:11:11-00:00"):
            application = TokenAuthFactory.create(
                contact_person="Amber Christman",
                email="amber.christman@callousdaoboys.com",
                phone_number="812371612",
                expire_date=datetime.date(2030, 1, 1),
                viewed_token_at=timezone.now(),
            )

        response = self.app.get(
            reverse(
                "admin:api_application_change", kwargs={"object_id": application.pk}
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, 200)

        form = response.forms["application_form"]
        form["api_access"].force_value([])
        form["permissions"].force_value([])
        form["initial-permissions"].force_value([])
        form["contact_person"] = "Jackie Buckalew"
        form["email"] = "jackie.buckalew@callousdaoboys.com"
        form["phone_number"] = "0123456789"
        form["expire_date"] = "2030-01-01"

        with freeze_time("2026-11-11T11:11:11-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        self.assertEqual(TimelineLogProxy.objects.count(), 2)
        read_log, update_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("read token audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": f"Application object ({application.pk})",
            }

            self.assertEqual(read_log.extra_data, expected_data)

        with self.subTest("update audit logging"):
            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": application.pk,
                    "email": "jackie.buckalew@callousdaoboys.com",
                    "created": "2025-11-11T11:11:11Z",
                    "expire_date": "2030-01-01",
                    "permissions": [],
                    "api_access": [],
                    "phone_number": "0123456789",
                    "last_modified": "2026-11-11T11:11:11Z",
                    "contact_person": "Jackie Buckalew",
                    "viewed_token_at": "2025-11-11T11:11:11Z",
                },
                "_cached_object_repr": f"Application object ({application.pk})",
            }
            self.assertEqual(update_log.extra_data, expected_data)

    def test_delete_log(self):
        assert not TimelineLogProxy.objects.exists()

        with freeze_time("2026-11-11T11:11:11-00:00"):
            application = TokenAuthFactory.create(
                contact_person="Daniel Hodsdon",
                email="daniel.hodsdon@callousdaoboys.com",
                phone_number="0123456789",
                expire_date=datetime.date(2030, 1, 1),
                viewed_token_at=timezone.now(),
                read_write_permission=True,
            )

        response = self.app.get(
            reverse(
                "admin:api_application_delete",
                kwargs={"object_id": application.pk},
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.delete,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": application.pk,
                "email": "daniel.hodsdon@callousdaoboys.com",
                "created": "2026-11-11T11:11:11Z",
                "expire_date": "2030-01-01",
                "permissions": ["read", "write"],
                "api_access": [],
                "phone_number": "0123456789",
                "last_modified": "2026-11-11T11:11:11Z",
                "contact_person": "Daniel Hodsdon",
                "viewed_token_at": "2026-11-11T11:11:11Z",
            },
            "_cached_object_repr": f"Application object ({application.pk})",
        }

        self.assertEqual(log.extra_data, expected_data)
