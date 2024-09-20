from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory

from ..constants import InformationCategoryOrigins
from ..models import CUSTOM_IDENTIFIER_URL_PREFIX, InformationCategory
from .factories import InformationCategoryFactory


@disable_admin_mfa()
class TestInformationCategoryAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(
            is_staff=True,
            is_superuser=True,
        )

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
        response = self.app.get(
            reverse(
                "admin:metadata_informationcategory_changelist",
            ),
            user=self.user,
        )
        form = response.forms["changelist-search"]

        with self.subTest("filter_on_naam"):
            form["q"] = "first item"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, information_category.identifier, 1)

        with self.subTest("filter_on_identifier"):
            form["q"] = information_category2.identifier
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, "second item", 1)

        with self.subTest("filter_on_oorsprong"):
            search_response = self.app.get(
                url,
                {"oorsprong__exact": InformationCategoryOrigins.value_list},
                user=self.user,
            )

            self.assertEqual(search_response.status_code, 200)

            # test the amount of rows present
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, information_category.identifier, 1)

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
        self.assertNotIn("naam", form.fields)

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
        response = form.submit("submit")

        self.assertEqual(response.status_code, 302)
        information_category.refresh_from_db()

        self.assertEqual(information_category.naam, "changed")
        self.assertEqual(information_category.naam_meervoud, "changed")
        self.assertEqual(information_category.definitie, "changed")

    def test_information_category_admin_create_item(self):
        response = self.app.get(
            reverse("admin:metadata_informationcategory_add"), user=self.user
        )
        form = response.forms["informationcategory_form"]

        form["naam"] = "new item"
        form["naam_meervoud"] = "new items"
        form["definitie"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
            "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur."
        )

        form.submit(name="_save")

        added_item = InformationCategory.objects.order_by("-pk").first()
        assert added_item is not None
        self.assertEqual(added_item.naam, "new item")
        self.assertTrue(added_item.identifier.startswith(CUSTOM_IDENTIFIER_URL_PREFIX))
        self.assertEqual(added_item.order, 0)
        self.assertEqual(added_item.naam_meervoud, "new items")
        self.assertEqual(
            added_item.definitie,
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
            "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur.",
        )
