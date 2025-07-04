from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy

from ..constants import InformationCategoryOrigins, OrganisationOrigins
from ..models import InformationCategory, Organisation
from .factories import InformationCategoryFactory, OrganisationFactory


@disable_admin_mfa()
class TestOrganisationAdminAuditLogging(WebTest):
    """
    Test that CRUD actions on organisations are audit-logged.

    We have a generic implementation in woo_publications.logging for this behaviour,
    for which the code coverage is provided through this test class.

    Additionally, there's a system check to ensure audit logging is added to our admin
    classes, which should cover the rest of the apps/models.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_admin_create(self):
        assert not TimelineLogProxy.objects.exists()
        reverse_url = reverse("admin:metadata_organisation_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["organisation_form"]
        form["naam"] = "organisation name"

        form.submit(name="_save")

        added_item = Organisation.objects.get()
        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.create,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": added_item.pk,
                "uuid": str(added_item.uuid),
                "identifier": added_item.identifier,
                "naam": "organisation name",
                "oorsprong": OrganisationOrigins.custom_entry,
                "is_actief": False,
                "rsin": "",
            },
            "_cached_object_repr": "organisation name",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_admin_update(self):
        assert not TimelineLogProxy.objects.exists()
        organisation = OrganisationFactory.create(
            naam="organisation name",
        )
        reverse_url = reverse(
            "admin:metadata_organisation_change",
            kwargs={"object_id": organisation.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["organisation_form"]
        form["naam"] = "changed name"
        form["is_actief"] = False

        form.submit(name="_save")

        organisation.refresh_from_db()

        self.assertEqual(TimelineLogProxy.objects.count(), 2)
        read_log, update_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("read audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": "organisation name",
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
                    "id": organisation.pk,
                    "uuid": str(organisation.uuid),
                    "identifier": organisation.identifier,
                    "naam": "changed name",
                    "oorsprong": OrganisationOrigins.custom_entry,
                    "is_actief": False,
                    "rsin": "",
                },
                "_cached_object_repr": "changed name",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_admin_delete(self):
        assert not TimelineLogProxy.objects.exists()

        organisation = OrganisationFactory.create(
            naam="soon to be deleted organisation",
        )
        reverse_url = reverse(
            "admin:metadata_organisation_delete",
            kwargs={"object_id": organisation.id},
        )

        response = self.app.get(reverse_url, user=self.user)

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
                "id": organisation.pk,
                "uuid": str(organisation.uuid),
                "identifier": organisation.identifier,
                "naam": "soon to be deleted organisation",
                "oorsprong": OrganisationOrigins.custom_entry,
                "is_actief": False,
                "rsin": "",
            },
            "_cached_object_repr": "soon to be deleted organisation",
        }

        self.assertEqual(log.extra_data, expected_data)


@disable_admin_mfa()
class TestInformatieCategorieenAdminAuditLogging(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_information_category_admin_create_log(self):
        assert not TimelineLogProxy.objects.exists()
        response = self.app.get(
            reverse("admin:metadata_informationcategory_add"), user=self.user
        )

        form = response.forms["informationcategory_form"]
        form["naam"] = "new item"
        form["naam_meervoud"] = "new items"
        form["definitie"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
            "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
            "eleifend eros sed consectetur."
        )
        form["bron_bewaartermijn"] = "Selectielijst gemeenten 2020"
        form["selectiecategorie"] = "20.1.2"
        form["archiefnominatie"].select(text=ArchiveNominationChoices.retain.label)
        form["bewaartermijn"] = 10
        form["toelichting_bewaartermijn"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
            "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
            "eleifend eros sed consectetur."
        )

        form.submit(name="_save")

        added_item = InformationCategory.objects.get()
        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.create,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": added_item.pk,
                "uuid": str(added_item.uuid),
                "identifier": added_item.identifier,
                "naam": "new item",
                "naam_meervoud": "new items",
                "omschrijving": "",
                "definitie": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris "
                    "risus nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris "
                    "interdum eleifend eros sed consectetur."
                ),
                "oorsprong": InformationCategoryOrigins.custom_entry,
                "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "20.1.2",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "bewaartermijn": 10,
                "toelichting_bewaartermijn": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris "
                    "risus nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris "
                    "interdum eleifend eros sed consectetur."
                ),
                "order": 0,
            },
            "_cached_object_repr": "new item",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_informatie_category_admin_change_log(
        self,
    ):
        assert not TimelineLogProxy.objects.exists()
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=InformationCategoryOrigins.custom_entry,
        )
        url = reverse(
            "admin:metadata_informationcategory_change",
            kwargs={"object_id": information_category.id},
        )

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.forms["informationcategory_form"]
        self.assertIn("naam", form.fields)

        # test if identifier isn't editable
        self.assertNotIn("identifier", form.fields)

        form["naam"] = "changed"
        form["naam_meervoud"] = "changed"
        form["definitie"] = "changed"
        form["bron_bewaartermijn"] = "Selectielijst gemeenten 2020"
        form["archiefnominatie"].select(text=ArchiveNominationChoices.retain.label)
        form["bewaartermijn"] = 10

        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        information_category.refresh_from_db()
        self.assertEqual(TimelineLogProxy.objects.count(), 2)
        read_log, update_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("read audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": "second item",
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
                    "id": information_category.pk,
                    "uuid": str(information_category.uuid),
                    "identifier": information_category.identifier,
                    "naam": "changed",
                    "naam_meervoud": "changed",
                    "omschrijving": "",
                    "definitie": "changed",
                    "oorsprong": InformationCategoryOrigins.custom_entry,
                    "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                    "selectiecategorie": "",
                    "archiefnominatie": ArchiveNominationChoices.retain,
                    "bewaartermijn": 10,
                    "toelichting_bewaartermijn": "",
                    "order": 0,
                },
                "_cached_object_repr": "changed",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_informatie_category_admin_delete_log(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="naam",
            naam_meervoud="namen",
            definitie="definitie",
            oorsprong=InformationCategoryOrigins.value_list,
            bron_bewaartermijn="test",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=10,
        )
        url = reverse(
            "admin:metadata_informationcategory_delete",
            kwargs={"object_id": information_category.id},
        )

        response = self.app.get(url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            InformationCategory.objects.filter(uuid=information_category.uuid).exists()
        )

        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.delete,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": information_category.pk,
                "uuid": str(information_category.uuid),
                "identifier": information_category.identifier,
                "naam": "naam",
                "naam_meervoud": "namen",
                "omschrijving": "",
                "definitie": "definitie",
                "oorsprong": InformationCategoryOrigins.value_list,
                "bron_bewaartermijn": "test",
                "selectiecategorie": "",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "bewaartermijn": 10,
                "toelichting_bewaartermijn": "",
                "order": 0,
            },
            "_cached_object_repr": "naam",
        }

        self.assertEqual(log.extra_data, expected_data)
