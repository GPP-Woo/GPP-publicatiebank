from unittest import skip

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.publications.tests.factories import PublicationFactory

from ..models import OrganisationUnit
from .factories import OrganisationUnitFactory, UserFactory


@disable_admin_mfa()
class TestOrganisationUnitAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_organisation_unit_admin_shows_items(self):
        OrganisationUnitFactory.create(identifier="one", naam="first org unit")
        OrganisationUnitFactory.create(identifier="two", naam="second org unit")
        response = self.app.get(
            reverse("admin:accounts_organisationunit_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-naam", 2)

    def test_organisation_unit_admin_search(self):
        OrganisationUnitFactory.create(identifier="one", naam="first org unit")
        OrganisationUnitFactory.create(identifier="two", naam="second org unit")
        reverse_url = reverse("admin:accounts_organisationunit_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]
        form["q"] = "two"

        search_response = form.submit()

        self.assertEqual(search_response.status_code, 200)
        self.assertContains(search_response, "field-naam", 1)
        self.assertContains(search_response, "second org unit", 1, html=True)

    def test_organisation_unit_admin_create(self):
        response = self.app.get(
            reverse("admin:accounts_organisationunit_add"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["organisationunit_form"]
        form["identifier"] = "identifier"
        form["naam"] = "naam"

        form.submit(name="_save")

        self.assertTrue(
            OrganisationUnit.objects.filter(
                identifier="identifier", naam="naam"
            ).exists()
        )

    def test_organisation_unit_admin_update(self):
        organisation_unit = OrganisationUnitFactory.create(
            identifier="one", naam="first org unit"
        )

        response = self.app.get(
            reverse(
                "admin:accounts_organisationunit_change",
                kwargs={"object_id": organisation_unit.pk},
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["organisationunit_form"]
        self.assertNotIn("identifier", form.fields)
        form["naam"] = "change"

        submit_response = form.submit(name="_save")

        self.assertEqual(submit_response.status_code, 302)
        organisation_unit.refresh_from_db()
        self.assertEqual(organisation_unit.naam, "change")

    def test_organisation_unit_admin_delete(self):
        org_unit = OrganisationUnitFactory.create(
            identifier="one", naam="first org unit"
        )
        reverse_url = reverse(
            "admin:accounts_organisationunit_delete",
            kwargs={"object_id": org_unit.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            OrganisationUnit.objects.filter(
                identifier="one", naam="first org unit"
            ).exists()
        )

    @skip("Not implemented yet.")
    def test_organisation_unit_admin_delete_when_having_items(self):
        org_unit = OrganisationUnitFactory.create(
            identifier="one", naam="first org unit"
        )
        PublicationFactory.create(eigenaar_groep=org_unit)
        reverse_url = reverse(
            "admin:accounts_organisationunit_delete",
            kwargs={"object_id": org_unit.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        title = _("Cannot delete %(name)s") % {
            "name": OrganisationUnit._meta.verbose_name
        }

        self.assertContains(response, title)
