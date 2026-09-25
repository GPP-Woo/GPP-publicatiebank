import datetime

from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.config.models import GlobalConfiguration
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.utils.tests.webtest import add_dynamic_field

from ..constants import LegalProcedureOptions
from ..models import InzageProcedure
from .factories import InzageProcedureFactory, PublicationFactory


@disable_admin_mfa()
@override_settings(LANGUAGE_CODE="en-en")
class InzageProcedureAdminWebTest(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "perspective_reaction_form_url": "http://www.example.com/perspective",
                "objection_reaction_form_url": "http://www.example.com/objection",
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_inzage_procedure_admin_shows_items(self):
        InzageProcedureFactory.create_batch(2)
        response = self.app.get(
            reverse("admin:publications_inzageprocedure_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-uuid", 2)

    def test_inzage_procedure_admin_search(self):
        publication = PublicationFactory.create(officiele_titel="marco!")
        publication_2 = PublicationFactory.create(officiele_titel="polo!")
        inzage_procedure_1 = InzageProcedureFactory.create(publicatie=publication)
        inzage_procedure_2 = InzageProcedureFactory.create(publicatie=publication_2)
        reverse_url = reverse("admin:publications_inzageprocedure_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter on uuid"):
            form["q"] = str(inzage_procedure_1.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            # showing up twice, because of the search bar and the list item on the page.
            self.assertContains(search_response, str(inzage_procedure_1.uuid))
            self.assertNotContains(search_response, str(inzage_procedure_2.uuid))

        with self.subTest("filter on publication uuid"):
            form["q"] = str(publication_2.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertNotContains(search_response, str(inzage_procedure_1.uuid))
            self.assertContains(search_response, str(inzage_procedure_2.uuid), 1)

        with self.subTest("filter on publication officiële titel"):
            form["q"] = "polo!"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertNotContains(search_response, str(inzage_procedure_1.uuid))
            self.assertContains(search_response, str(inzage_procedure_2.uuid), 1)

    def test_inzage_procedure_admin_list_filter(self):
        inzage_procedure_1 = InzageProcedureFactory.create(
            automatisch_intrekken=False,
            beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
            datum_begin_inzagetermijn=datetime.date(2026, 9, 13),
            datum_einde_inzagetermijn=datetime.date(2026, 10, 13),
        )
        inzage_procedure_2 = InzageProcedureFactory.create(
            automatisch_intrekken=True,
            beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
            datum_begin_inzagetermijn=datetime.date(2026, 9, 14),
            datum_einde_inzagetermijn=datetime.date(2026, 10, 14),
        )
        inzage_procedure_3 = InzageProcedureFactory.create(
            automatisch_intrekken=True,
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
            datum_begin_inzagetermijn=datetime.date(2026, 9, 15),
            datum_einde_inzagetermijn=datetime.date(2026, 10, 15),
        )
        reverse_url = reverse("admin:publications_inzageprocedure_changelist")
        self.app.set_user(user=self.user)

        with self.subTest("filter on begin datum") and freeze_time("2026-09-13"):
            response = self.app.get(reverse_url)
            self.assertEqual(response.status_code, 200)

            search_response = response.click(description=_("Today"), index=0)
            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on datum_begin_inzagetermijn
            self.assertIn(
                "datum_begin_inzagetermijn",
                search_response.request.environ["QUERY_STRING"],
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(inzage_procedure_1.uuid), 1)

        with self.subTest("filter on eind datum") and freeze_time("2026-10-14"):
            response = self.app.get(reverse_url)
            self.assertEqual(response.status_code, 200)

            search_response = response.click(description=_("Today"), index=1)
            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on datum_begin_inzagetermijn
            self.assertIn(
                "datum_einde_inzagetermijn",
                search_response.request.environ["QUERY_STRING"],
            )

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(inzage_procedure_2.uuid), 1)

        response = self.app.get(reverse_url)
        self.assertEqual(response.status_code, 200)

        with self.subTest("filter on automatically redact"):
            search_response = response.click(description=_("No"), index=0)

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(inzage_procedure_1.uuid), 1)

        with self.subTest("filter on legal procedure"):
            search_response = response.click(
                description=str(LegalProcedureOptions.objection.label), index=0
            )

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-uuid", 1)
            self.assertContains(search_response, str(inzage_procedure_3.uuid), 1)

    def test_inzage_procedure_admin_create(self):
        publication_1, publication_2 = PublicationFactory.create_batch(2)
        InzageProcedureFactory.create(publicatie=publication_2)
        url = reverse("admin:publications_inzageprocedure_add")

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)
        form = response.forms["inzageprocedure_form"]

        with self.subTest("create inzage procedure"):
            form["publicatie"].force_value(publication_1.id)
            form["url_bekendmaking"] = "https://example.com/bekendmaking"
            form["toelichting"] = "bla"
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.objection
            form["url_reactieformulier"] = "https://example.com/reactieformulier"
            form["datum_begin_inzagetermijn"] = "2008-09-10"
            form["datum_einde_inzagetermijn"] = "2010-09-8"
            form["automatisch_intrekken"] = True

            submit_response = form.submit(name="_save")

            self.assertRedirects(
                submit_response,
                reverse("admin:publications_inzageprocedure_changelist"),
            )

            inzage_procedure = InzageProcedure.objects.last()
            assert inzage_procedure

            self.assertEqual(inzage_procedure.publicatie, publication_1)
            self.assertEqual(
                inzage_procedure.url_bekendmaking, "https://example.com/bekendmaking"
            )
            self.assertEqual(inzage_procedure.toelichting, "bla")
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.objection,
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "https://example.com/reactieformulier",
            )
            self.assertEqual(
                inzage_procedure.datum_begin_inzagetermijn, datetime.date(2008, 9, 10)
            )
            self.assertEqual(
                inzage_procedure.datum_einde_inzagetermijn, datetime.date(2010, 9, 8)
            )
            self.assertEqual(inzage_procedure.automatisch_intrekken, True)

        with self.subTest(
            "create inzage procedure for publication with an existing inzage procedure"
        ):
            form["publicatie"].force_value(publication_2.id)
            form["url_bekendmaking"] = "https://example.com/bekendmaking"
            form["toelichting"] = "bla"
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.objection
            form["url_reactieformulier"] = "https://example.com/reactieformulier"
            form["datum_begin_inzagetermijn"] = "10-09-2008"
            form["datum_einde_inzagetermijn"] = "08-09-2010"
            form["automatisch_intrekken"] = True

            submit_response = form.submit(name="_save")

            self.assertFormError(
                submit_response.context["adminform"],
                "publicatie",
                "Access procedure with this Publication already exists.",
            )

    def test_inzage_procedure_admin_create_auto_fills_url_reactieformulier_field(self):
        publication = PublicationFactory.create()
        url = reverse("admin:publications_inzageprocedure_add")

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)
        form = response.forms["inzageprocedure_form"]

        form["publicatie"].force_value(publication.id)
        form["url_bekendmaking"] = "https://example.com/bekendmaking"
        form["toelichting"] = "bla"
        form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.perspective
        form["url_reactieformulier"] = ""
        form["datum_begin_inzagetermijn"] = "2008-09-10"
        form["datum_einde_inzagetermijn"] = "2026-04-27"
        form["automatisch_intrekken"] = True

        submit_response = form.submit(name="_save")

        self.assertRedirects(
            submit_response,
            reverse("admin:publications_inzageprocedure_changelist"),
        )

        inzage_procedure = InzageProcedure.objects.get()

        self.assertEqual(
            inzage_procedure.url_reactieformulier, "http://www.example.com/perspective"
        )

    def test_end_date_auto_selects_workday(self):
        publication = PublicationFactory.create()
        url = reverse("admin:publications_inzageprocedure_add")

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)
        form = response.forms["inzageprocedure_form"]

        form["publicatie"].force_value(publication.id)
        form["url_bekendmaking"] = "https://example.com/bekendmaking"
        form["toelichting"] = "bla"
        form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.objection
        form["url_reactieformulier"] = "https://example.com/reactieformulier"
        form["datum_begin_inzagetermijn"] = "2008-09-10"
        form["datum_einde_inzagetermijn"] = "2026-04-27"
        form["automatisch_intrekken"] = True

        submit_response = form.submit(name="_save")

        self.assertRedirects(
            submit_response,
            reverse("admin:publications_inzageprocedure_changelist"),
        )

        inzage_procedure = InzageProcedure.objects.get()

        self.assertEqual(
            inzage_procedure.datum_einde_inzagetermijn, datetime.date(2026, 4, 28)
        )

    def test_end_date_cannot_be_earlier_then_start_day(self):
        publication = PublicationFactory.create()
        url = reverse("admin:publications_inzageprocedure_add")

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)
        form = response.forms["inzageprocedure_form"]

        with self.subTest("create inzage procedure"):
            form["publicatie"].force_value(publication.id)
            form["url_bekendmaking"] = "https://example.com/bekendmaking"
            form["toelichting"] = "bla"
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.objection
            form["url_reactieformulier"] = "https://example.com/reactieformulier"
            form["datum_begin_inzagetermijn"] = "2008-09-10"
            form["datum_einde_inzagetermijn"] = "2008-07-10"
            form["automatisch_intrekken"] = True

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 200)
            self.assertFormError(
                submit_response.context["adminform"],
                "datum_einde_inzagetermijn",
                _("The end date cannot happen before the start date."),
            )

    def test_inzage_procedure_admin_update(self):
        publication_1, publication_2 = PublicationFactory.create_batch(2)
        inzage_procedure = InzageProcedureFactory.create(
            publicatie=publication_1,
            url_bekendmaking="https://example.com/bekendmaking",
            toelichting="bla",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
            url_reactieformulier="https://example.com/reactieformulier",
            datum_begin_inzagetermijn=datetime.date(2008, 9, 10),
            datum_einde_inzagetermijn=datetime.date(2010, 9, 8),
            automatisch_intrekken=True,
        )

        url = reverse(
            "admin:publications_inzageprocedure_change",
            kwargs={"object_id": inzage_procedure.pk},
        )

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)
        form = response.forms["inzageprocedure_form"]

        with self.subTest("update inzage procedure"):
            form["publicatie"].force_value(publication_2.id)
            form["url_bekendmaking"] = "https://example.com/bekendmaking/changed/"
            form["toelichting"] = "changed"
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.perspective
            form["url_reactieformulier"] = (
                "https://example.com/reactieformulier/changed/"
            )
            form["datum_begin_inzagetermijn"] = "2018-09-10"
            form["datum_einde_inzagetermijn"] = "2020-09-8"
            form["automatisch_intrekken"] = False

            update_response = form.submit(name="_save")

            self.assertEqual(update_response.status_code, 302)
            self.assertRedirects(
                update_response,
                reverse("admin:publications_inzageprocedure_changelist"),
            )
            inzage_procedure.refresh_from_db()
            self.assertEqual(inzage_procedure.publicatie, publication_2)
            self.assertEqual(
                inzage_procedure.url_bekendmaking,
                "https://example.com/bekendmaking/changed/",
            )
            self.assertEqual(inzage_procedure.toelichting, "changed")
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.perspective,
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "https://example.com/reactieformulier/changed/",
            )
            self.assertEqual(
                inzage_procedure.datum_begin_inzagetermijn, datetime.date(2018, 9, 10)
            )
            self.assertEqual(
                inzage_procedure.datum_einde_inzagetermijn, datetime.date(2020, 9, 8)
            )
            self.assertEqual(inzage_procedure.automatisch_intrekken, False)

        with self.subTest(
            "update inzage procedure to publication which already is linked"
        ):
            linked_publication = PublicationFactory.create()
            InzageProcedureFactory.create(publicatie=linked_publication)

            form["publicatie"].force_value(linked_publication.id)

            submit_response = form.submit(name="_save")

            self.assertFormError(
                submit_response.context["adminform"],
                "publicatie",
                "Access procedure with this Publication already exists.",
            )

    def test_inzage_procedure_admin_update_auto_fills_url_reactieformulier_field(self):
        inzage_procedure = InzageProcedureFactory.create(
            url_reactieformulier="https://example.com/bekendmaking/",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
        )

        url = reverse(
            "admin:publications_inzageprocedure_change",
            kwargs={"object_id": inzage_procedure.pk},
        )

        response = self.app.get(url, user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.forms["inzageprocedure_form"]

        with self.subTest(
            "update url_bekendmaking while providing beschikbaar_rechtsmiddel "
            "doesn't fall back on global settings"
        ):
            form["url_reactieformulier"] = "https://example.com/bekendmaking/changed/"
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.perspective

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 302)
            inzage_procedure.refresh_from_db()
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "https://example.com/bekendmaking/changed/",
            )
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.perspective,
            )

        with self.subTest(
            "updating beschikbaar_rechtsmiddel without changing url_bekendmaking "
            "doesn't alter the url field"
        ):
            # explicitly state that the url_bekendmaking's field contains data
            form["url_reactieformulier"] = "https://example.com/bekendmaking/changed/"
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.objection

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 302)
            inzage_procedure.refresh_from_db()
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "https://example.com/bekendmaking/changed/",
            )
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.objection,
            )

        with self.subTest(
            "updating beschikbaar_rechtsmiddel without setting url_bekendmaking "
            "to be empty does alter the url field"
        ):
            # explicitly state that the url_bekendmaking's field contains data
            form["url_reactieformulier"] = ""
            form["beschikbaar_rechtsmiddel"] = LegalProcedureOptions.perspective

            submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_code, 302)
            inzage_procedure.refresh_from_db()
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "http://www.example.com/perspective",
            )
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.perspective,
            )

    def test_inzage_procedure_admin_delete(self):
        inzage_procedure = InzageProcedureFactory.create()
        url = reverse(
            "admin:publications_inzageprocedure_delete",
            kwargs={"object_id": inzage_procedure.pk},
        )

        response = self.app.get(url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            InzageProcedure.objects.filter(uuid=inzage_procedure.uuid).exists()
        )

    def test_inline_inzage_procedure_create(self):
        assert InzageProcedure.objects.count() == 0

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
        form["inzageprocedure-TOTAL_FORMS"] = "1"  # we're adding one, dynamically
        add_dynamic_field(
            form,
            "inzageprocedure-0-url_bekendmaking",
            "https://example.com/bekendmaking",
        )
        add_dynamic_field(form, "inzageprocedure-0-toelichting", "bla")
        add_dynamic_field(
            form,
            "inzageprocedure-0-beschikbaar_rechtsmiddel",
            LegalProcedureOptions.objection,
        )
        add_dynamic_field(
            form, "inzageprocedure-0-datum_begin_inzagetermijn", "2008-09-10"
        )
        add_dynamic_field(
            form, "inzageprocedure-0-datum_einde_inzagetermijn", "2026-04-27"
        )
        add_dynamic_field(form, "inzageprocedure-0-automatisch_intrekken", "1")

        create_response = form.submit(name="_save")

        self.assertEqual(create_response.status_code, 302)

        inzage_procedure = InzageProcedure.objects.get()

        self.assertEqual(inzage_procedure.publicatie, publication)
        self.assertEqual(
            inzage_procedure.url_bekendmaking, "https://example.com/bekendmaking"
        )
        self.assertEqual(inzage_procedure.toelichting, "bla")
        self.assertEqual(
            inzage_procedure.beschikbaar_rechtsmiddel,
            LegalProcedureOptions.objection,
        )
        self.assertEqual(
            inzage_procedure.url_reactieformulier, "http://www.example.com/objection"
        )
        self.assertEqual(
            inzage_procedure.datum_begin_inzagetermijn, datetime.date(2008, 9, 10)
        )
        self.assertEqual(
            inzage_procedure.datum_einde_inzagetermijn, datetime.date(2026, 4, 28)
        )
        self.assertEqual(inzage_procedure.automatisch_intrekken, True)

    def test_inline_inzage_procedure_create_provide_url_reactieformulier_manually(self):
        assert InzageProcedure.objects.count() == 0

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
        form["inzageprocedure-TOTAL_FORMS"] = "1"  # we're adding one, dynamically
        add_dynamic_field(form, "inzageprocedure-0-toelichting", "bla")
        add_dynamic_field(
            form,
            "inzageprocedure-0-beschikbaar_rechtsmiddel",
            LegalProcedureOptions.objection,
        )
        add_dynamic_field(
            form,
            "inzageprocedure-0-url_reactieformulier",
            "https://www.example.com/some/path",
        )
        add_dynamic_field(
            form, "inzageprocedure-0-datum_begin_inzagetermijn", "2008-09-10"
        )
        add_dynamic_field(
            form, "inzageprocedure-0-datum_einde_inzagetermijn", "2026-04-27"
        )

        create_response = form.submit(name="_save")

        self.assertEqual(create_response.status_code, 302)

        inzage_procedure = InzageProcedure.objects.get()

        self.assertEqual(inzage_procedure.publicatie, publication)
        self.assertEqual(
            inzage_procedure.beschikbaar_rechtsmiddel,
            LegalProcedureOptions.objection,
        )
        self.assertEqual(
            inzage_procedure.url_reactieformulier, "https://www.example.com/some/path"
        )

    def test_inline_inzage_procedure_update(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
        )
        inzage_procedure = InzageProcedureFactory.create(publicatie=publication)
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]

        with self.subTest("update entire object"):
            add_dynamic_field(
                form,
                "inzageprocedure-0-url_bekendmaking",
                "https://example.com/bekendmaking/changed",
            )
            add_dynamic_field(form, "inzageprocedure-0-toelichting", "changed")
            add_dynamic_field(
                form,
                "inzageprocedure-0-beschikbaar_rechtsmiddel",
                LegalProcedureOptions.perspective,
            )
            add_dynamic_field(
                form, "inzageprocedure-0-datum_begin_inzagetermijn", "2008-09-10"
            )
            add_dynamic_field(
                form, "inzageprocedure-0-datum_einde_inzagetermijn", "2026-04-27"
            )
            add_dynamic_field(form, "inzageprocedure-0-automatisch_intrekken", "")

            update_response = form.submit(name="_save")

            self.assertEqual(update_response.status_code, 302)

            inzage_procedure.refresh_from_db()

            self.assertEqual(inzage_procedure.publicatie, publication)
            self.assertEqual(
                inzage_procedure.url_bekendmaking,
                "https://example.com/bekendmaking/changed",
            )
            self.assertEqual(inzage_procedure.toelichting, "changed")
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.perspective,
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "http://www.example.com/perspective",
            )
            self.assertEqual(
                inzage_procedure.datum_begin_inzagetermijn, datetime.date(2008, 9, 10)
            )
            self.assertEqual(
                inzage_procedure.datum_einde_inzagetermijn, datetime.date(2026, 4, 28)
            )
            self.assertEqual(inzage_procedure.automatisch_intrekken, False)

        with self.subTest("provide url_reactieformulier in update uses said data"):
            add_dynamic_field(
                form,
                "inzageprocedure-0-beschikbaar_rechtsmiddel",
                LegalProcedureOptions.objection,
            )
            add_dynamic_field(
                form,
                "inzageprocedure-0-url_reactieformulier",
                "https://example.com/some/path",
            )

            update_response = form.submit(name="_save")

            self.assertEqual(update_response.status_code, 302)

            inzage_procedure.refresh_from_db()

            self.assertEqual(inzage_procedure.publicatie, publication)
            self.assertEqual(
                inzage_procedure.beschikbaar_rechtsmiddel,
                LegalProcedureOptions.objection,
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "https://example.com/some/path",
            )

    def test_inline_inzage_procedure_delete(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
        )
        inzage_procedure = InzageProcedureFactory.create(publicatie=publication)
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["inzageprocedure-0-DELETE"] = True

        delete_response = form.submit(name="_save")

        self.assertEqual(delete_response.status_code, 302)

        self.assertFalse(
            InzageProcedure.objects.filter(pk=inzage_procedure.id).exists()
        )
