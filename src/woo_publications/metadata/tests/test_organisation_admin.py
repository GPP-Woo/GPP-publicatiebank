from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory

from ..constants import OrganisationOrigins
from ..models import CUSTOM_ORGANISATION_URL_PREFIX, Organisation
from .factories import OrganisationFactory


@disable_admin_mfa()
class TestOrganisationAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_organisation_admin_show_items(self):
        OrganisationFactory.create(
            naam="first item",
            oorsprong=OrganisationOrigins.municipality_list,
            is_actief=True,
        )
        OrganisationFactory.create(
            naam="second item",
            oorsprong=OrganisationOrigins.custom_entry,
            is_actief=True,
        )
        response = self.app.get(
            reverse(
                "admin:metadata_organisation_changelist",
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        # test the amount of rows present
        self.assertContains(response, "field-identifier", 2)

    def test_organisation_admin_show_item_search(self):
        organisation = OrganisationFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            oorsprong=OrganisationOrigins.municipality_list,
            is_actief=True,
        )
        organisation2 = OrganisationFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=OrganisationOrigins.custom_entry,
            is_actief=False,
        )
        url = reverse("admin:metadata_organisation_changelist")

        response = self.app.get(url, user=self.user)

        form = response.forms["changelist-search"]

        with self.subTest("filter_on_naam"):
            form["q"] = "first item"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            # because of django 5.2 url fields now are clickable links
            # so the identifier comes across as the name and href of the <a> tag
            self.assertContains(search_response, organisation.identifier, 2)

        with self.subTest("filter_on_identifier"):
            form["q"] = organisation2.identifier
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            # because of django 5.2 the checkbox for selecting items for action
            # now has the clickable link name in its area label
            self.assertContains(search_response, "second item", 2)

    def test_organisation_admin_list_filters(self):
        self.app.set_user(user=self.user)

        organisation = OrganisationFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            oorsprong=OrganisationOrigins.municipality_list,
            is_actief=True,
        )
        OrganisationFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=OrganisationOrigins.custom_entry,
            is_actief=False,
        )
        url = reverse("admin:metadata_organisation_changelist")

        response = self.app.get(url)

        with self.subTest("filter_on_oorsprong"):
            search_response = response.click(description=_("Municipality list"))

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            # because of django 5.2 url fields now are clickable links
            # so the identifier comes across as the name and href of the <a> tag
            self.assertContains(search_response, organisation.identifier, 2)

        with self.subTest("filter_on_is_actief"):
            search_response = response.click(
                description=_("Yes"), href="is_actief__exact=1"
            )

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            # because of django 5.2 url fields now are clickable links
            # so the identifier comes across as the name and href of the <a> tag
            self.assertContains(search_response, organisation.identifier, 2)

    def test_organisation_admin_waardenlijst_items_can_update_extra_fields(
        self,
    ):
        for waardenlijst_origin in [
            OrganisationOrigins.municipality_list,
            OrganisationOrigins.oorg_list,
            OrganisationOrigins.so_list,
        ]:
            with self.subTest(waardenlijst_origin):
                organisation = OrganisationFactory.create(
                    oorsprong=waardenlijst_origin,
                    is_actief=True,
                )
                url = reverse(
                    "admin:metadata_organisation_change",
                    kwargs={"object_id": organisation.id},
                )

                response = self.app.get(url, user=self.user)
                self.assertEqual(response.status_code, 200)

                form = response.forms["organisation_form"]
                form["is_actief"] = False
                form["rsin"] = "000000000"
                self.assertNotIn("naam", form.fields)

                form.submit(name="_save")

                organisation.refresh_from_db()

                self.assertEqual(organisation.is_actief, False)
                self.assertEqual(organisation.rsin, "000000000")

    def test_organisation_admin_can_update_item_with_oorsprong_zelf_toegevoegd(
        self,
    ):
        organisation = OrganisationFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=OrganisationOrigins.custom_entry,
            is_actief=True,
        )
        url = reverse(
            "admin:metadata_organisation_change",
            kwargs={"object_id": organisation.id},
        )

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.forms["organisation_form"]
        self.assertIn("naam", form.fields)

        # test if identifier isn't editable
        self.assertNotIn("identifier", form.fields)

        form["naam"] = "changed"
        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        organisation.refresh_from_db()

        self.assertEqual(organisation.naam, "changed")

    def test_organisation_admin_create_item(self):
        response = self.app.get(
            reverse("admin:metadata_organisation_add"), user=self.user
        )

        form = response.forms["organisation_form"]
        form["naam"] = "new item"

        form.submit(name="_save")

        added_item = Organisation.objects.order_by("-pk").first()
        assert added_item is not None
        self.assertEqual(added_item.naam, "new item")
        self.assertTrue(
            added_item.identifier.startswith(CUSTOM_ORGANISATION_URL_PREFIX)
        )
        self.assertFalse(added_item.is_actief)
        self.assertEqual(added_item.oorsprong, OrganisationOrigins.custom_entry)
