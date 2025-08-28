from unittest.mock import MagicMock, call, patch

from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.models import OrganisationMember
from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.config.models import GlobalConfiguration
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from ..models import Document, Publication
from .factories import DocumentFactory, PublicationFactory


@disable_admin_mfa()
class TestPublicationsAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_publications_admin_shows_items(self):
        PublicationFactory.create(
            eigenaar=self.organisation_member,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        PublicationFactory.create(
            eigenaar=self.organisation_member,
            officiele_titel="title two",
            verkorte_titel="two",
            omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
            "facilisis mollis urna.",
        )
        response = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-uuid", 2)

    def test_admin_shows_link_to_gpp_app(self):
        config = GlobalConfiguration.get_solo()
        self.addCleanup(config.clear_cache)
        config.gpp_app_publication_url_template = "https://example.com/<UUID>"
        config.save()
        publication = PublicationFactory.create()

        response = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _("Open in app"))
        self.assertContains(response, f"https://example.com/{publication.uuid}")

    def test_admin_shows_link_to_gpp_burgerportaal(self):
        config = GlobalConfiguration.get_solo()
        self.addCleanup(config.clear_cache)
        config.gpp_burgerportaal_publication_url_template = "https://example.com/<UUID>"
        config.save()
        publication = PublicationFactory.create()

        response = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _("Open in burgerportaal"))
        self.assertContains(response, f"https://example.com/{publication.uuid}")

    def test_publications_admin_search(self):
        org_member_1 = OrganisationMemberFactory.create(
            identifier="test-identifier",
            naam="test-naam",
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = PublicationFactory.create(
                eigenaar=org_member_1,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
            )
        reverse_url = reverse("admin:publications_publication_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter on uuid"):
            form["q"] = str(publication2.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-officiele_titel", 1)
            # because of django 5.2 the checkbox for selecting items for action
            # now has the clickable link name in its area label
            self.assertContains(search_response, "title two", 2)

        with self.subTest("filter on officiele_title"):
            form["q"] = "title one"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication.uuid), 1)

        with self.subTest("filter on verkorte_titel"):
            form["q"] = "one"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication.uuid), 1)

        with self.subTest("filter on owner identifier"):
            form["q"] = org_member_1.identifier
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

    def test_publication_list_filter(self):
        self.app.set_user(user=self.user)
        with freeze_time("2024-09-24T12:00:00-00:00"):
            PublicationFactory.create(
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum="2024-09-24",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.concept,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2024-09-25",
            )
        reverse_url = reverse("admin:publications_publication_changelist")

        with freeze_time("2024-09-25T00:14:00-00:00"):
            response = self.app.get(reverse_url)

        self.assertEqual(response.status_code, 200)

        with self.subTest("filter on registratiedatum"):
            search_response = response.click(description=_("Today"), index=0)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on registratiedatum
            self.assertIn(
                "registratiedatum", search_response.request.environ["QUERY_STRING"]
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

        with self.subTest("filter on publicatiestatus"):
            search_response = response.click(
                description=str(PublicationStatusOptions.concept.label)
            )

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

        with self.subTest("filter on archiefnominatie"):
            search_response = response.click(
                description=str(ArchiveNominationChoices.retain.label)
            )

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

        with self.subTest("filter on archiefactiedatum"):
            search_response = response.click(description=_("Today"), index=1)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on archiefactiedatum
            self.assertIn(
                "archiefactiedatum", search_response.request.environ["QUERY_STRING"]
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(publication2.uuid), 1)

        with self.subTest("filter on archiefactiedatum filter on last year"):
            publication_retention_last_year = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title three",
                verkorte_titel="three",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum="2023-09-24",
            )

            search_response = response.click(description=_("Last year"), index=0)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on archiefactiedatum
            self.assertIn(
                "archiefactiedatum", search_response.request.environ["QUERY_STRING"]
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(
                search_response, str(publication_retention_last_year.uuid), 1
            )

    @freeze_time("2024-09-25T00:14:00-00:00")
    def test_publications_admin_create(self):
        ic, ic2, ic3 = InformationCategoryFactory.create_batch(
            3,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        deactivated_organisation = OrganisationFactory.create(is_actief=False)
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

        with self.subTest("assert that revoked isn't a valid publicatiestatus option"):
            self.assertEqual(len(form["publicatiestatus"].options), 2)
            self.assertIn(
                (
                    PublicationStatusOptions.concept.value,
                    False,
                    PublicationStatusOptions.concept.label,
                ),
                form["publicatiestatus"].options,
            )
            self.assertIn(
                (
                    PublicationStatusOptions.published.value,
                    False,
                    PublicationStatusOptions.published.label,
                ),
                form["publicatiestatus"].options,
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
            form["publicatiestatus"].select(
                text=PublicationStatusOptions.published.label
            )
            form["publisher"] = str(organisation.pk)
            form["verantwoordelijke"] = str(organisation.pk)
            form["opsteller"] = str(organisation.pk)
            form["officiele_titel"] = "The official title of this publication"
            form["verkorte_titel"] = "The title"
            form["omschrijving"] = (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur."
            )
            form["bron_bewaartermijn"] = ("Selectielijst gemeenten 2020",)
            form["selectiecategorie"] = ("20.1.2",)
            form["archiefnominatie"].select(text=ArchiveNominationChoices.retain.label)
            form["archiefactiedatum"] = ("2025-01-01",)
            form["toelichting_bewaartermijn"] = ("extra data",)
            form["datum_begin_geldigheid"] = "2024-09-24"
            form["datum_einde_geldigheid"] = "2024-09-24"

            form.submit(name="_save")

            added_item = Publication.objects.order_by("-pk").first()
            assert added_item is not None
            self.assertEqual(
                added_item.publicatiestatus, PublicationStatusOptions.published
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
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur.",
            )
            self.assertEqual(str(added_item.datum_begin_geldigheid), "2024-09-24")
            self.assertEqual(str(added_item.datum_einde_geldigheid), "2024-09-24")
            self.assertEqual(
                str(added_item.registratiedatum), "2024-09-25 00:14:00+00:00"
            )
            self.assertEqual(
                str(added_item.laatst_gewijzigd_datum), "2024-09-25 00:14:00+00:00"
            )
            # Test if the fields get overwritten from the input by the IC
            self.assertEqual(added_item.bron_bewaartermijn, "bewaartermijn")
            self.assertEqual(added_item.selectiecategorie, "selectiecategorie")
            self.assertEqual(
                added_item.archiefnominatie, ArchiveNominationChoices.retain
            )
            self.assertEqual(str(added_item.archiefactiedatum), "2029-09-25")
            self.assertEqual(added_item.toelichting_bewaartermijn, "toelichting")
            # Test if eigenaar field gets automatically set
            self.assertEqual(added_item.eigenaar, self.organisation_member)

    def test_create_concept_with_only_officiele_titel(self):
        reverse_url = reverse("admin:publications_publication_add")
        response = self.app.get(reverse_url, user=self.user)

        form = response.forms["publication_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
        form["officiele_titel"] = "test"

        submit_response = form.submit(name="_save")

        self.assertEqual(submit_response.status_code, 302)
        self.assertTrue(Publication.objects.exists())

    @patch("woo_publications.publications.admin.index_publication.delay")
    def test_publication_create_schedules_index_task(
        self, mock_index_publication_delay: MagicMock
    ):
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["publisher"] = str(organisation.pk)
        form["verantwoordelijke"] = str(organisation.pk)
        form["opsteller"] = str(organisation.pk)
        form["officiele_titel"] = "The official title of this publication"
        form["verkorte_titel"] = "The title"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
            "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
            "eleifend eros sed consectetur.",
        )
        form["bron_bewaartermijn"] = "Selectielijst gemeenten 2020"
        form["selectiecategorie"] = "20.1.2"
        form["archiefnominatie"].select(text=ArchiveNominationChoices.retain.label)
        form["archiefactiedatum"] = "2025-01-01"
        form["toelichting_bewaartermijn"] = "extra data"

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertRedirects(
            add_response,
            reverse("admin:publications_publication_changelist"),
        )

        added_item = Publication.objects.order_by("-pk").first()
        assert added_item is not None
        mock_index_publication_delay.assert_called_once_with(
            publication_id=added_item.pk
        )

    def test_publications_admin_update(self):
        org_member_1 = OrganisationMemberFactory(
            identifier="test-identifier",
            naam="test-naam",
        )
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="changed",
            selectiecategorie="changed",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=1,
            toelichting_bewaartermijn="changed",
        )
        organisation, organisation2 = OrganisationFactory.create_batch(
            2, is_actief=True
        )
        deactivated_organisation = OrganisationFactory.create(is_actief=False)
        with freeze_time("2024-09-25T00:14:00-00:00"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                publicatiestatus=PublicationStatusOptions.published,
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
            form["publicatiestatus"].select(
                text=PublicationStatusOptions.published.label
            )
            form["eigenaar"].force_value([org_member_1.pk])
            form["publisher"] = str(organisation2.pk)
            form["verantwoordelijke"] = str(organisation2.pk)
            form["opsteller"] = str(organisation2.pk)
            form["officiele_titel"] = "changed official title"
            form["verkorte_titel"] = "changed short title"
            form["omschrijving"] = "changed description"
            # Values will be overwritten because ic got changed
            form["bron_bewaartermijn"] = "changed bron bewaartermijn"
            form["selectiecategorie"] = "changed selectiecategory"
            form["archiefnominatie"].select(text=ArchiveNominationChoices.destroy.label)
            form["archiefactiedatum"] = "2025-01-01"
            form["toelichting_bewaartermijn"] = "changed toelichting bewaartermijn"

            with freeze_time("2024-09-27T00:14:00-00:00"):
                response = form.submit(name="_save")

            self.assertEqual(response.status_code, 302)

            publication.refresh_from_db()
            self.assertEqual(
                publication.publicatiestatus, PublicationStatusOptions.published
            )
            self.assertQuerySetEqual(publication.informatie_categorieen.all(), [ic])
            self.assertEqual(publication.eigenaar, org_member_1)
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
            self.assertEqual(publication.bron_bewaartermijn, "changed")
            self.assertEqual(publication.selectiecategorie, "changed")
            self.assertEqual(
                publication.archiefnominatie, ArchiveNominationChoices.destroy
            )
            self.assertEqual(str(publication.archiefactiedatum), "2025-09-25")
            self.assertEqual(
                publication.toelichting_bewaartermijn,
                "changed",
            )

    def test_publications_admin_update_concept_to_published_with_ic(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="changed",
            selectiecategorie="changed",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=1,
            toelichting_bewaartermijn="changed",
        )
        organisation = OrganisationFactory.create(is_actief=True)

        with freeze_time("2024-09-25T00:14:00-00:00"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[],
                publicatiestatus=PublicationStatusOptions.concept,
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

        form["informatie_categorieen"].force_value([ic.pk])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)

        # use different time when the publication was published
        with freeze_time("2024-09-30T00:14:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        publication.refresh_from_db()
        self.assertEqual(
            publication.publicatiestatus, PublicationStatusOptions.published
        )
        self.assertQuerySetEqual(publication.informatie_categorieen.all(), [ic])
        self.assertEqual(publication.bron_bewaartermijn, "changed")
        self.assertEqual(publication.selectiecategorie, "changed")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(str(publication.archiefactiedatum), "2025-09-30")
        self.assertEqual(
            publication.toelichting_bewaartermijn,
            "changed",
        )

    @patch("woo_publications.publications.admin.index_publication.delay")
    def test_publication_update_schedules_index_task(
        self, mock_index_publication_delay: MagicMock
    ):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["officiele_titel"] = "changed official title"

        with self.captureOnCommitCallbacks(execute=True):
            update_response = form.submit(name="_save")

        self.assertRedirects(
            update_response,
            reverse("admin:publications_publication_changelist"),
        )

        mock_index_publication_delay.assert_called_once_with(
            publication_id=publication.pk
        )

    @patch("woo_publications.publications.admin.index_document.delay")
    def test_publication_update_publisher_or_ic_schedules_document_index_task(
        self, mock_index_document_delay: MagicMock
    ):
        ic_1, ic_2 = InformationCategoryFactory.create_batch(2)
        publisher_1, publisher_2 = OrganisationFactory.create_batch(2, is_actief=True)
        publication = PublicationFactory.create(
            informatie_categorieen=[ic_1],
            publisher=publisher_1,
            officiele_titel="title one",
        )
        document_1, document_2 = DocumentFactory.create_batch(2, publicatie=publication)
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        with self.subTest(
            "update value other than publisher or ic doesn't trigger schedule"
        ):
            form["officiele_titel"] = "changed official title"

            with self.captureOnCommitCallbacks(execute=True):
                update_response = form.submit(name="_save")

            self.assertRedirects(
                update_response,
                reverse("admin:publications_publication_changelist"),
            )

            mock_index_document_delay.assert_not_called()

        with self.subTest("update publisher triggers schedule"):
            mock_index_document_delay.reset_mock()
            form["publisher"] = str(publisher_2.pk)

            with self.captureOnCommitCallbacks(execute=True):
                update_response = form.submit(name="_save")

            self.assertRedirects(
                update_response,
                reverse("admin:publications_publication_changelist"),
            )
            mock_index_document_delay.assert_has_calls(
                [
                    call(document_id=document_1.pk),
                    call(document_id=document_2.pk),
                ],
                any_order=True,
            )

        with self.subTest("update information category triggers schedule"):
            mock_index_document_delay.reset_mock()
            form["informatie_categorieen"].force_value([ic_1.pk, ic_2.pk])

            with self.captureOnCommitCallbacks(execute=True):
                update_response = form.submit(name="_save")

            self.assertRedirects(
                update_response,
                reverse("admin:publications_publication_changelist"),
            )
            mock_index_document_delay.assert_has_calls(
                [
                    call(document_id=document_1.pk),
                    call(document_id=document_2.pk),
                ],
                any_order=True,
            )

    @patch("woo_publications.publications.admin.remove_publication_from_index.delay")
    def test_publication_update_schedules_remove_from_index_task(
        self, mock_remove_publication_from_index_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            uuid="b89742ec-9dd2-4617-86c5-e39e1b4d9907",
            publicatiestatus=PublicationStatusOptions.published,
            informatie_categorieen=[InformationCategoryFactory.create()],
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["publicatiestatus"] = PublicationStatusOptions.revoked

        with self.captureOnCommitCallbacks(execute=True):
            update_response = form.submit(name="_save")

        self.assertRedirects(
            update_response,
            reverse("admin:publications_publication_changelist"),
        )

        mock_remove_publication_from_index_delay.assert_called_once_with(
            publication_id=publication.pk
        )

    @patch(
        "woo_publications.publications.tasks.remove_document_from_index.delay",
        return_value=None,
    )
    def test_publications_when_revoking_publication_documents_also_get_revoked(  # noqa: E501
        self,
        mock_remove_document_from_index_delay: MagicMock,
    ):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.published,
        )
        published_document = DocumentFactory.create(
            publicatie=publication, publicatiestatus=PublicationStatusOptions.published
        )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        publication.refresh_from_db()
        published_document.refresh_from_db()

        self.assertEqual(publication.publicatiestatus, PublicationStatusOptions.revoked)
        self.assertEqual(
            published_document.publicatiestatus, PublicationStatusOptions.revoked
        )

        mock_remove_document_from_index_delay.assert_called_once_with(
            document_id=published_document.pk
        )

    def test_publications_admin_not_allowed_to_update_when_publication_is_revoked(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            revoked=True,
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

    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_publications_admin_delete(
        self,
        mock_remove_from_index_by_uuid_delay: MagicMock,
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        published_document = DocumentFactory.create(
            publicatie=publication,
            publicatiestatus=PublicationStatusOptions.published,
        )
        reverse_url = reverse(
            "admin:publications_publication_delete",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Publication.objects.filter(uuid=publication.uuid).exists())
        self.assertFalse(Document.objects.filter(uuid=published_document.uuid).exists())

        self.assertEqual(mock_remove_from_index_by_uuid_delay.call_count, 2)
        mock_remove_from_index_by_uuid_delay.assert_any_call(
            model_name="Publication", uuid=str(publication.uuid)
        )
        mock_remove_from_index_by_uuid_delay.assert_any_call(
            model_name="Document", uuid=str(published_document.uuid)
        )

    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_publications_admin_delete_unpublished(
        self,
        mock_remove_from_index_by_uuid_delay: MagicMock,
    ):
        publication = PublicationFactory.create(revoked=True)
        reverse_url = reverse(
            "admin:publications_publication_delete",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)
        form = response.forms[1]

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit()

        self.assertEqual(response.status_code, 302)
        mock_remove_from_index_by_uuid_delay.assert_not_called()

    @patch("woo_publications.publications.admin.index_publication.delay")
    def test_index_bulk_action(self, mock_index_publication_delay: MagicMock):
        published_publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        PublicationFactory.create(revoked=True)
        PublicationFactory.create(publicatiestatus=PublicationStatusOptions.concept)
        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [pub.pk for pub in Publication.objects.all()]
        form["action"] = "sync_to_index"
        with self.captureOnCommitCallbacks(execute=True):
            form.submit()

        mock_index_publication_delay.assert_called_once_with(
            publication_id=published_publication.pk
        )

    @patch("woo_publications.publications.admin.remove_publication_from_index.delay")
    def test_remove_from_index_bulk_action(
        self, mock_remove_publication_from_index_delay: MagicMock
    ):
        PublicationFactory.create(publicatiestatus=PublicationStatusOptions.published)
        PublicationFactory.create(publicatiestatus=PublicationStatusOptions.concept)
        PublicationFactory.create(revoked=True)
        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Publication.objects.all()]
        form["action"] = "remove_from_index"
        with self.captureOnCommitCallbacks(execute=True):
            form.submit()

        for pub_id in Publication.objects.values_list("pk", flat=True):
            mock_remove_publication_from_index_delay.assert_any_call(
                publication_id=pub_id, force=True
            )

    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_bulk_removal_action(self, remove_from_index_by_uuid_delay: MagicMock):
        pub1 = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        pub2 = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        pub3 = PublicationFactory.create(revoked=True)

        DocumentFactory.create(
            publicatie=pub1, publicatiestatus=PublicationStatusOptions.published
        )
        DocumentFactory.create(
            publicatie=pub2, publicatiestatus=PublicationStatusOptions.concept
        )
        DocumentFactory.create(
            publicatie=pub3, publicatiestatus=PublicationStatusOptions.revoked
        )

        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Publication.objects.all()]
        form["action"] = "delete_selected"

        response = form.submit()

        with self.captureOnCommitCallbacks(execute=True):
            confirmation_form = response.forms[1]
            confirmation_form.submit()

        for pub_uuid in Publication.objects.values_list("uuid", flat=True):
            remove_from_index_by_uuid_delay.assert_any_call(
                model_name="Publication", uuid=str(pub_uuid), force=True
            )

        for doc_uuid in Document.objects.values_list("uuid", flat=True):
            remove_from_index_by_uuid_delay.assert_any_call(
                model_name="Document", uuid=doc_uuid, force=True
            )

    @patch("woo_publications.publications.tasks.remove_document_from_index.delay")
    @patch("woo_publications.publications.admin.remove_publication_from_index.delay")
    def test_publication_revoke_action(
        self,
        mock_remove_publication_from_index_delay: MagicMock,
        mock_remove_document_from_index_delay: MagicMock,
    ):
        published_publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        concept_publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        revoked_publication = PublicationFactory.create(revoked=True)

        published_document = DocumentFactory.create(
            publicatie=published_publication,
            publicatiestatus=PublicationStatusOptions.published,
        )
        concept_document = DocumentFactory.create(
            publicatie=concept_publication,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        revoked_document = DocumentFactory.create(
            publicatie=revoked_publication,
            publicatiestatus=PublicationStatusOptions.revoked,
        )

        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [pub.pk for pub in Publication.objects.all()]
        form["action"] = "revoke"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit()

        published_publication.refresh_from_db()
        concept_publication.refresh_from_db()
        revoked_publication.refresh_from_db()
        published_document.refresh_from_db()
        concept_document.refresh_from_db()
        revoked_document.refresh_from_db()

        self.assertEqual(mock_remove_publication_from_index_delay.call_count, 2)
        self.assertEqual(
            revoked_publication.publicatiestatus, PublicationStatusOptions.revoked
        )
        for pub in [published_publication, concept_publication]:
            self.assertEqual(pub.publicatiestatus, PublicationStatusOptions.revoked)
            mock_remove_publication_from_index_delay.assert_any_call(
                publication_id=pub.pk, force=True
            )

        self.assertEqual(mock_remove_document_from_index_delay.call_count, 2)
        # document with publication status doesn't change its status
        self.assertEqual(
            concept_document.publicatiestatus, PublicationStatusOptions.revoked
        )
        self.assertEqual(
            revoked_document.publicatiestatus, PublicationStatusOptions.revoked
        )
        self.assertEqual(
            published_document.publicatiestatus, PublicationStatusOptions.revoked
        )
        mock_remove_document_from_index_delay.assert_has_calls(
            [
                call(document_id=published_document.pk),
                call(document_id=concept_document.pk),
            ],
            any_order=True,
        )

    def test_change_owner_action(self):
        org_member_1 = OrganisationMemberFactory.create(
            naam="test-naam", identifier="test-identifier"
        )
        pub1 = PublicationFactory.create(eigenaar=self.organisation_member)
        pub2 = PublicationFactory.create(eigenaar=self.organisation_member)
        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )

        form = changelist.forms["changelist-form"]
        form["_selected_action"] = [pub1.pk, pub2.pk]
        form["action"] = "change_owner"

        response = form.submit()

        self.assertEqual(response.status_code, 200)

        with self.subTest("no data supplied"):
            confirmation_form = response.forms[1]

            error_response = confirmation_form.submit()

            self.assertFormError(
                error_response.context["form"],
                None,
                _("You need to provide a valid 'owner' or 'identifier' and 'name'."),
            )

        with self.subTest("only identifier supplied"):
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].force_value([])
            confirmation_form["identifier"] = "admin@admin.admin"
            confirmation_form["naam"] = ""

            error_response = confirmation_form.submit()

            self.assertFormError(
                error_response.context["form"], "naam", _("This field is required.")
            )

        with self.subTest("only naam supplied"):
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].force_value([])
            confirmation_form["identifier"] = ""
            confirmation_form["naam"] = "admin@admin.admin"

            error_response = confirmation_form.submit()

            self.assertFormError(
                error_response.context["form"],
                "identifier",
                _("This field is required."),
            )

        with self.subTest("identifier and naam supplied"):
            self.assertFalse(
                OrganisationMember.objects.filter(
                    identifier="admin@admin.admin", naam="admin"
                ).exists()
            )
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].force_value([])
            confirmation_form["identifier"] = "admin@admin.admin"
            confirmation_form["naam"] = "admin"
            confirmation_form.submit()

            pub1.refresh_from_db()
            pub2.refresh_from_db()

            self.assertEqual(response.status_code, 200)
            org_member_2 = OrganisationMember.objects.get(
                identifier="admin@admin.admin", naam="admin"
            )
            self.assertEqual(pub1.eigenaar, org_member_2)
            self.assertEqual(pub2.eigenaar, org_member_2)

        with self.subTest("eigenaar supplied"):
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].select(text=str(org_member_1))
            confirmation_form["identifier"] = ""
            confirmation_form["naam"] = ""

            confirmation_form.submit()

            pub1.refresh_from_db()
            pub2.refresh_from_db()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(pub1.eigenaar, org_member_1)
            self.assertEqual(pub2.eigenaar, org_member_1)

    @patch("woo_publications.publications.tasks.update_document_rsin.delay")
    def test_publication_update_publisher_schedules_document_rsin_update_task(
        self, mock_update_document_rsin_delay: MagicMock
    ):
        self.addCleanup(GlobalConfiguration.clear_cache)
        config = GlobalConfiguration.get_solo()
        config.organisation_rsin = "112345670"
        config.save()

        ic = InformationCategoryFactory.create()
        publisher = OrganisationFactory.create(rsin="000000000", is_actief=True)
        new_publisher_with_rsin = OrganisationFactory.create(
            rsin="123456782", is_actief=True
        )
        new_publisher_without_rsin = OrganisationFactory.create(rsin="", is_actief=True)
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
            publisher=publisher,
            informatie_categorieen=[ic],
        )
        published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            publisher=publisher,
            informatie_categorieen=[ic],
        )
        concept_document = DocumentFactory.create(
            publicatie=concept,
            publicatiestatus=PublicationStatusOptions.concept,
            with_registered_document=True,
        )
        published_document = DocumentFactory.create(
            publicatie=published,
            publicatiestatus=PublicationStatusOptions.published,
            with_registered_document=True,
        )

        with self.subTest("update concept with new publisher rsin"):
            detail_url = reverse(
                "admin:publications_publication_change",
                kwargs={"object_id": concept.id},
            )
            response = self.app.get(detail_url, user=self.user)

            self.assertEqual(response.status_code, 200)

            form = response.forms["publication_form"]
            form["publisher"] = str(new_publisher_with_rsin.pk)

            with self.captureOnCommitCallbacks(execute=True):
                response = form.submit(name="_save")

            self.assertEqual(response.status_code, 302)
            mock_update_document_rsin_delay.assert_called_with(
                document_id=concept_document.pk, rsin="123456782"
            )

        with self.subTest("update published with global config rsin"):
            detail_url = reverse(
                "admin:publications_publication_change",
                kwargs={"object_id": published.id},
            )
            response = self.app.get(detail_url, user=self.user)

            self.assertEqual(response.status_code, 200)

            form = response.forms["publication_form"]
            form["publisher"] = str(new_publisher_without_rsin.pk)

            with self.captureOnCommitCallbacks(execute=True):
                response = form.submit(name="_save")

            self.assertEqual(response.status_code, 302)
            mock_update_document_rsin_delay.assert_called_with(
                document_id=published_document.pk, rsin="112345670"
            )

    @patch("woo_publications.publications.tasks.update_document_rsin.delay")
    def test_publication_regular_update_does_not_schedules_document_rsin_update_task(
        self, mock_update_document_rsin_delay: MagicMock
    ):
        ic = InformationCategoryFactory.create()
        publisher = OrganisationFactory.create(rsin="000000000", is_actief=True)
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept,
            publisher=publisher,
            informatie_categorieen=[ic],
        )
        published = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            publisher=publisher,
            informatie_categorieen=[ic],
        )
        DocumentFactory.create(
            publicatie=concept,
            publicatiestatus=PublicationStatusOptions.concept,
            with_registered_document=True,
        )
        DocumentFactory.create(
            publicatie=published,
            publicatiestatus=PublicationStatusOptions.published,
            with_registered_document=True,
        )

        with self.subTest("update concept with new publisher rsin"):
            detail_url = reverse(
                "admin:publications_publication_change",
                kwargs={"object_id": concept.id},
            )
            response = self.app.get(detail_url, user=self.user)

            self.assertEqual(response.status_code, 200)

            form = response.forms["publication_form"]
            form["officiele_titel"] = "changed official title"

            with self.captureOnCommitCallbacks(execute=True):
                response = form.submit(name="_save")

            self.assertEqual(response.status_code, 302)
            mock_update_document_rsin_delay.assert_not_called()

        with self.subTest("update published with global config rsin"):
            detail_url = reverse(
                "admin:publications_publication_change",
                kwargs={"object_id": published.id},
            )
            response = self.app.get(detail_url, user=self.user)

            self.assertEqual(response.status_code, 200)

            form = response.forms["publication_form"]
            form["officiele_titel"] = "changed official title"

            with self.captureOnCommitCallbacks(execute=True):
                response = form.submit(name="_save")

            self.assertEqual(response.status_code, 302)
            mock_update_document_rsin_delay.assert_not_called()


@disable_admin_mfa()
class TestPublicationRequiredFields(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_create_publicatie_status_concept(self):
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
        submit_response = form.submit("_save")

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            submit_response.context["adminform"],
            "officiele_titel",
            _("This field is required."),
        )

        # IC and Publisher didn't contain any errors when not provided
        self.assertFormError(
            submit_response.context["adminform"], "informatie_categorieen", []
        )
        self.assertFormError(submit_response.context["adminform"], "publisher", [])

    def test_create_publicatie_status_published(self):
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        submit_response = form.submit("_save")

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            submit_response.context["adminform"],
            "officiele_titel",
            _("This field is required."),
        )
        self.assertFormError(
            submit_response.context["adminform"],
            "informatie_categorieen",
            _("This field is required."),
        )
        self.assertFormError(
            submit_response.context["adminform"],
            "publisher",
            _("This field is required."),
        )

    def test_update_publicatie_status_concept(self):
        publication = PublicationFactory.create(
            publisher=None,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["officiele_titel"] = None
        submit_response = form.submit("_save")

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            submit_response.context["adminform"],
            "officiele_titel",
            _("This field is required."),
        )

        # IC and Publisher didn't contain any errors when not provided
        self.assertFormError(
            submit_response.context["adminform"], "informatie_categorieen", []
        )
        self.assertFormError(submit_response.context["adminform"], "publisher", [])

    def test_update_publicatie_status_published(self):
        publication = PublicationFactory.create(
            publisher=None,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["officiele_titel"] = None
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        submit_response = form.submit("_save")

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            submit_response.context["adminform"],
            "officiele_titel",
            _("This field is required."),
        )
        self.assertFormError(
            submit_response.context["adminform"],
            "informatie_categorieen",
            _("This field is required."),
        )
        self.assertFormError(
            submit_response.context["adminform"],
            "publisher",
            _("This field is required."),
        )

    def test_update_publicatie_status_revoke(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.published,
        )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["officiele_titel"] = None
        form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)
        form["informatie_categorieen"].force_value([])
        form["publisher"].force_value("")

        submit_response = form.submit("_save")

        self.assertEqual(response.status_code, 200)

        self.assertFormError(
            submit_response.context["adminform"],
            "officiele_titel",
            _("This field is required."),
        )
        self.assertFormError(
            submit_response.context["adminform"],
            "informatie_categorieen",
            _("This field is required."),
        )
        self.assertFormError(
            submit_response.context["adminform"],
            "publisher",
            _("This field is required."),
        )
