from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from furl import furl
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.constants import ArchiveNominationChoices

from ..constants import InformationCategoryOrigins
from ..models import CUSTOM_CATEGORY_IDENTIFIER_URL_PREFIX, InformationCategory
from .factories import InformationCategoryFactory


@disable_admin_mfa()
class TestInformationCategoryAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_information_category_admin_show_items(self):
        InformationCategoryFactory.create(
            naam="first item",
            oorsprong=InformationCategoryOrigins.value_list,
        )
        InformationCategoryFactory.create(
            naam="second item",
            oorsprong=InformationCategoryOrigins.custom_entry,
        )
        response = self.app.get(
            reverse(
                "admin:metadata_informationcategory_changelist",
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        # test the amount of rows present
        self.assertContains(response, "field-identifier", 2)

    def test_information_category_admin_show_item_search(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            oorsprong=InformationCategoryOrigins.value_list,
        )
        information_category2 = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=InformationCategoryOrigins.custom_entry,
        )
        url = reverse("admin:metadata_informationcategory_changelist")

        response = self.app.get(url, user=self.user)

        form = response.forms["changelist-search"]

        with self.subTest("filter on naam"):
            form["q"] = "first item"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            # because of django 5.2 url fields now are clickable links
            # so the identifier comes across as the name and href of the <a> tag
            self.assertContains(search_response, information_category.identifier, 2)

        with self.subTest("filter on identifier"):
            form["q"] = information_category2.identifier
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-naam", 1)
            # because of django 5.2 the checkbox for selecting items for action
            # now has the clickable link name in its area label
            self.assertContains(search_response, "second item", 2)

    def test_information_category_admin_list_filter(self):
        self.app.set_user(user=self.user)

        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            oorsprong=InformationCategoryOrigins.value_list,
        )
        InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=InformationCategoryOrigins.custom_entry,
        )
        url = reverse("admin:metadata_informationcategory_changelist")

        response = self.app.get(url)

        with self.subTest("filter on oorsprong"):
            search_response = response.click(description=_("Value list"))

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            # because of django 5.2 url fields now are clickable links
            # so the identifier comes across as the name and href of the <a> tag
            self.assertContains(search_response, information_category.identifier, 2)

    def test_information_category_admin_can_not_update_item_with_oorsprong_waardenlijst(
        self,
    ):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/1",
            naam="first item",
            oorsprong=InformationCategoryOrigins.value_list,
        )
        url = reverse(
            "admin:metadata_informationcategory_change",
            kwargs={"object_id": information_category.id},
        )

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.forms["informationcategory_form"]
        # zelf_toegevoegd specific editable fields:
        self.assertNotIn("naam", form.fields)
        self.assertNotIn("naam_meervoud", form.fields)
        self.assertNotIn("definitie", form.fields)
        # always accessible fields:
        self.assertIn("omschrijving", form.fields)
        self.assertIn("bron_bewaartermijn", form.fields)
        self.assertIn("selectiecategorie", form.fields)
        self.assertIn("archiefnominatie", form.fields)
        self.assertIn("bewaartermijn", form.fields)
        self.assertIn("toelichting_bewaartermijn", form.fields)

    def test_information_category_admin_can_update_item_with_oorsprong_zelf_toegevoegd(
        self,
    ):
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

        self.assertEqual(information_category.naam, "changed")
        self.assertEqual(information_category.naam_meervoud, "changed")
        self.assertEqual(information_category.definitie, "changed")
        self.assertEqual(
            information_category.bron_bewaartermijn, "Selectielijst gemeenten 2020"
        )
        self.assertEqual(
            information_category.archiefnominatie, ArchiveNominationChoices.retain
        )
        self.assertEqual(information_category.bewaartermijn, 10)

    def test_information_category_admin_create_item(self):
        response = self.app.get(
            reverse("admin:metadata_informationcategory_add"), user=self.user
        )
        form = response.forms["informationcategory_form"]

        with self.subTest("bewaartermijn exeeds max length of 3"):
            expected_error = _(
                "Ensure this value is less than or equal to %(limit_value)s."
            ) % {"limit_value": "999"}

            form["bewaartermijn"] = 1000
            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"], "bewaartermijn", expected_error
            )

        with self.subTest("happy flow"):
            form["naam"] = "new item"
            form["naam_meervoud"] = "new items"
            form["definitie"] = (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur."
            )
            form["bron_bewaartermijn"] = "Selectielijst gemeenten 2020"
            form["archiefnominatie"].select(text=ArchiveNominationChoices.retain.label)
            form["bewaartermijn"] = 10

            form.submit(name="_save")

            added_item = InformationCategory.objects.order_by("-pk").first()
            assert added_item is not None
            self.assertEqual(added_item.naam, "new item")
            self.assertTrue(
                added_item.identifier.startswith(CUSTOM_CATEGORY_IDENTIFIER_URL_PREFIX)
            )
            self.assertEqual(added_item.order, 0)
            self.assertEqual(added_item.naam_meervoud, "new items")
            self.assertEqual(
                added_item.definitie,
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur.",
            )
            self.assertEqual(
                added_item.bron_bewaartermijn, "Selectielijst gemeenten 2020"
            )
            self.assertEqual(
                added_item.archiefnominatie, ArchiveNominationChoices.retain
            )
            self.assertEqual(added_item.bewaartermijn, 10)

    def test_information_category_admin_delete_item(self):
        information_category = InformationCategoryFactory.create(
            identifier="https://www.example.com/waardenlijsten/2",
            naam="second item",
            oorsprong=InformationCategoryOrigins.value_list,
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


@disable_admin_mfa()
class InformationCategoryAPIResourceListAdminTests(WebTest):
    def test_staff_user_required(self):
        bad_users = (
            None,
            UserFactory.create(),
        )
        url = reverse("admin:metadata_informationcategory_iotendpoints")

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
        self.client.force_login(staff_user_without_permissions)
        url = reverse("admin:metadata_informationcategory_iotendpoints")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)

    def test_lists_api_endpoints(self):
        user = UserFactory.create(superuser=True)
        url = reverse("admin:metadata_informationcategory_iotendpoints")
        InformationCategoryFactory.create(
            naam="unique snowflake", uuid="7aa923ea-9e72-4523-9ef9-f7e1e74cf53a"
        )

        response = self.app.get(url, user=user)

        self.assertContains(response, "unique snowflake")
        self.assertContains(
            response,
            (
                "http://testserver/catalogi/api/v1/informatieobjecttypen/"
                "7aa923ea-9e72-4523-9ef9-f7e1e74cf53a"
            ),
        )
