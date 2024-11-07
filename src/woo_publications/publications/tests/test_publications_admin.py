from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.api.constants import PublicationStatusOptions
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..models import Publication
from .factories import PublicationFactory


@disable_admin_mfa()
class TestPublicationsAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_publications_admin_shows_items(self):
        PublicationFactory.create(
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        PublicationFactory.create(
            officiele_titel="title two",
            verkorte_titel="two",
            omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
        )
        response = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-uuid", 2)

    def test_publications_admin_search(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = PublicationFactory.create(
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
            )
        reverse_url = reverse("admin:publications_publication_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter_on_officiele_title"):
            form["q"] = "title one"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication.uuid), 1)

        with self.subTest("filter_on_verkorte_titel"):
            form["q"] = "two"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

        with self.subTest("filter_on_verkorte_titel"):
            form["q"] = str(publication.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, "title one", 1)

    def test_publication_list_filter(self):
        self.app.set_user(user=self.user)

        with freeze_time("2024-09-24T12:00:00-00:00"):
            PublicationFactory.create(
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = PublicationFactory.create(
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
            )
        reverse_url = reverse("admin:publications_publication_changelist")

        with freeze_time("2024-09-25T00:14:00-00:00"):
            response = self.app.get(reverse_url)

        self.assertEqual(response.status_code, 200)

        with self.subTest("filter_on_registratiedatum"):
            search_response = response.click(description=_("Today"), index=0)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on registratiedatum
            self.assertIn(
                "registratiedatum", search_response.request.environ["QUERY_STRING"]
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

    @freeze_time("2024-09-25T00:14:00-00:00")
    def test_publications_admin_create(self):
        ic, ic2, ic3 = InformationCategoryFactory.create_batch(3)
        organisation = OrganisationFactory(is_actief=True)
        deactivated_organisation = OrganisationFactory(is_actief=False)
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        with self.subTest("no information_categorieen given results in form error"):
            form["informatie_categorieen"] = ""

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"],
                "informatie_categorieen",
                _("This field is required."),
            )

        with self.subTest("trying to create a revoked publication results in errors"):
            form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"],
                None,
                _("You cannot create a {} publication.").format(
                    PublicationStatusOptions.revoked.label.lower()
                ),
            )

        with self.subTest(
            "organisation fields only has active organisation as options"
        ):
            form_fields = submit_response.context["adminform"].form.fields

            with self.subTest("publisher"):
                publisher_qs = form_fields["publisher"].queryset
                self.assertIn(organisation, publisher_qs)
                self.assertNotIn(deactivated_organisation, publisher_qs)

            with self.subTest("verantwoordelijke"):
                verantwoordelijke_qs = form_fields["verantwoordelijke"].queryset
                self.assertIn(organisation, verantwoordelijke_qs)
                self.assertNotIn(deactivated_organisation, verantwoordelijke_qs)

        with self.subTest("opsteller field has all organisation as options"):
            form_fields = response.context["adminform"].form.fields
            opsteller_qs = form_fields["opsteller"].queryset
            self.assertIn(organisation, opsteller_qs)
            self.assertIn(deactivated_organisation, opsteller_qs)

        with self.subTest("complete data creates publication"):
            # Force the value because the select box options get loaded in with js
            form["informatie_categorieen"].force_value([ic.id, ic2.id, ic3.id])
            form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
            form["publisher"].select(text=organisation.naam)
            form["verantwoordelijke"].select(text=organisation.naam)
            form["opsteller"].select(text=organisation.naam)
            form["officiele_titel"] = "The official title of this publication"
            form["verkorte_titel"] = "The title"
            form["omschrijving"] = (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
                "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur."
            )

            form.submit(name="_save")

            added_item = Publication.objects.order_by("-pk").first()
            assert added_item is not None
            self.assertEqual(
                added_item.publicatiestatus, PublicationStatusOptions.concept
            )
            self.assertQuerySetEqual(
                added_item.informatie_categorieen.all(), [ic, ic2, ic3], ordered=False
            )
            self.assertEqual(
                added_item.officiele_titel, "The official title of this publication"
            )
            self.assertEqual(added_item.verkorte_titel, "The title")
            self.assertEqual(
                added_item.omschrijving,
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
                "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur.",
            )
            self.assertEqual(
                str(added_item.registratiedatum), "2024-09-25 00:14:00+00:00"
            )
            self.assertEqual(
                str(added_item.laatst_gewijzigd_datum), "2024-09-25 00:14:00+00:00"
            )

    def test_publications_admin_update(self):
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        organisation, organisation2 = OrganisationFactory.create_batch(
            2, is_actief=True
        )
        deactivated_organisation = OrganisationFactory.create(is_actief=False)
        with freeze_time("2024-09-25T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        with self.subTest("no information_categorieen given results in form error"):
            form["informatie_categorieen"] = ""

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"],
                "informatie_categorieen",
                _("This field is required."),
            )

        with self.subTest(
            "organisation fields only has active organisation as options"
        ):
            form_fields = response.context["adminform"].form.fields

            with self.subTest("publisher"):
                publisher_qs = form_fields["publisher"].queryset
                self.assertIn(organisation, publisher_qs)
                self.assertIn(organisation2, publisher_qs)
                self.assertNotIn(deactivated_organisation, publisher_qs)

            with self.subTest("verantwoordelijke"):
                verantwoordelijke_qs = form_fields["verantwoordelijke"].queryset
                self.assertIn(organisation, verantwoordelijke_qs)
                self.assertIn(organisation2, verantwoordelijke_qs)
                self.assertNotIn(deactivated_organisation, verantwoordelijke_qs)

        with self.subTest("opsteller field has all organisation as options"):
            form_fields = response.context["adminform"].form.fields
            opsteller_qs = form_fields["opsteller"].queryset
            self.assertIn(organisation, opsteller_qs)
            self.assertIn(organisation2, opsteller_qs)
            self.assertIn(deactivated_organisation, opsteller_qs)

        with self.subTest("no publisher given results in form error"):
            form["publisher"] = ""

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"],
                "publisher",
                _("This field is required."),
            )

        with self.subTest("complete data updates publication"):
            form["informatie_categorieen"].select_multiple(texts=[ic.naam])
            form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
            form["publisher"].select(text=organisation2.naam)
            form["verantwoordelijke"].select(text=organisation2.naam)
            form["opsteller"].select(text=organisation2.naam)
            form["officiele_titel"] = "changed official title"
            form["verkorte_titel"] = "changed short title"
            form["omschrijving"] = "changed description"

            with freeze_time("2024-09-27T00:14:00-00:00"):
                response = form.submit(name="_save")

            self.assertEqual(response.status_code, 302)

            publication.refresh_from_db()
            self.assertEqual(
                publication.publicatiestatus, PublicationStatusOptions.concept
            )
            self.assertQuerySetEqual(publication.informatie_categorieen.all(), [ic])
            self.assertFalse(
                publication.informatie_categorieen.filter(pk=ic2.pk).exists()
            )
            self.assertEqual(publication.officiele_titel, "changed official title")
            self.assertEqual(publication.verkorte_titel, "changed short title")
            self.assertEqual(publication.omschrijving, "changed description")
            self.assertEqual(
                str(publication.registratiedatum), "2024-09-25 00:14:00+00:00"
            )
            self.assertEqual(
                str(publication.laatst_gewijzigd_datum), "2024-09-27 00:14:00+00:00"
            )

    def test_publications_admin_not_allowed_to_update_when_publication_is_revoked(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.revoked,
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        response = form.submit(name="_save", expect_errors=True)

        self.assertEqual(response.status_code, 403)

    def test_publications_admin_delete(self):
        publication = PublicationFactory.create(
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        reverse_url = reverse(
            "admin:publications_publication_delete",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Publication.objects.filter(uuid=publication.uuid).exists())
