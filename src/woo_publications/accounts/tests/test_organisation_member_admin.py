from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.publications.tests.factories import PublicationFactory

from ..models import OrganisationMember
from .factories import OrganisationMemberFactory, UserFactory


@disable_admin_mfa()
class TestOrganisationMemberAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_organisation_member_admin_shows_items(self):
        OrganisationMemberFactory.create(identifier="one", naam="first org member")
        OrganisationMemberFactory.create(identifier="two", naam="second org member")
        response = self.app.get(
            reverse("admin:accounts_organisationmember_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-naam", 2)

    def test_organisation_member_admin_search(self):
        OrganisationMemberFactory.create(identifier="one", naam="first org member")
        OrganisationMemberFactory.create(identifier="two", naam="second org member")
        reverse_url = reverse("admin:accounts_organisationmember_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]
        form["q"] = "two"

        search_response = form.submit()

        self.assertEqual(search_response.status_code, 200)
        self.assertContains(search_response, "field-naam", 1)
        self.assertContains(search_response, "second org member", 1, html=True)

    def test_organisation_member_admin_create(self):
        response = self.app.get(
            reverse("admin:accounts_organisationmember_add"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["organisationmember_form"]
        form["identifier"] = "identifier"
        form["naam"] = "naam"

        form.submit(name="_save")

        self.assertTrue(
            OrganisationMember.objects.filter(
                identifier="identifier", naam="naam"
            ).exists()
        )

    def test_organisation_member_admin_update(self):
        organisation_member = OrganisationMemberFactory.create(
            identifier="one", naam="first org member"
        )

        response = self.app.get(
            reverse(
                "admin:accounts_organisationmember_change",
                kwargs={"object_id": organisation_member.pk},
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["organisationmember_form"]
        self.assertNotIn("identifier", form.fields)
        form["naam"] = "change"

        submit_response = form.submit(name="_save")

        self.assertEqual(submit_response.status_code, 302)
        organisation_member.refresh_from_db()
        self.assertEqual(organisation_member.naam, "change")

    def test_organisation_member_admin_delete(self):
        org_member = OrganisationMemberFactory.create(
            identifier="one", naam="first org member"
        )
        reverse_url = reverse(
            "admin:accounts_organisationmember_delete",
            kwargs={"object_id": org_member.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            OrganisationMember.objects.filter(
                identifier="one", naam="first org member"
            ).exists()
        )

    def test_organisation_member_admin_delete_when_having_items(self):
        org_member = OrganisationMemberFactory.create(
            identifier="one", naam="first org member"
        )
        PublicationFactory.create(
            eigenaar=org_member,
        )
        reverse_url = reverse(
            "admin:accounts_organisationmember_delete",
            kwargs={"object_id": org_member.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        title = _("Cannot delete %(name)s") % {
            "name": OrganisationMember._meta.verbose_name
        }

        self.assertContains(response, title)
