"""
Configuration admin (smoke)tests.
"""

from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import LegalRemedyOptions
from woo_publications.publications.tests.factories import InzageProcedureFactory

from ..models import GlobalConfiguration


@disable_admin_mfa()
class SmokeTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_initial_config_creation_does_not_crash(self):
        assert not GlobalConfiguration.objects.exists(), "Expected no config to exist"
        url = reverse("admin:config_globalconfiguration_change", args=(1,))

        self.app.get(url, user=self.user)

        self.assertTrue(
            GlobalConfiguration.objects.exists(),
            "Expected the configuration instance to be created",
        )

    def test_back_filling_urls(self):
        empty_perspective = InzageProcedureFactory.create(
            url_reactieformulier="",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.perspective,
        )
        filled_perspective = InzageProcedureFactory.create(
            url_reactieformulier="http://www.example.com/perspective",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.perspective,
        )
        empty_objection = InzageProcedureFactory.create(
            url_reactieformulier="",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
        )
        filled_objection = InzageProcedureFactory.create(
            url_reactieformulier="http://www.example.com/objection",
            beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
        )
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)

        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        response = self.app.get(url, user=self.user)

        form = response.forms["globalconfiguration_form"]

        with self.subTest("Save with empty url values triggers back fill function"):
            form["documents_api_service"] = document_service.pk
            form["organisation_rsin"] = "000000000"
            form["gpp_search_service"] = search_service.pk
            form["perspective_reaction_form_url"] = "http://www.config.net/perspective"
            form["objection_reaction_form_url"] = "http://www.config.net/objection"

            with self.captureOnCommitCallbacks(execute=True):
                submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_int, 302)

            empty_perspective.refresh_from_db()
            filled_perspective.refresh_from_db()
            empty_objection.refresh_from_db()
            filled_objection.refresh_from_db()

            self.assertEqual(
                empty_perspective.url_reactieformulier,
                "http://www.config.net/perspective",
            )
            self.assertEqual(
                filled_perspective.url_reactieformulier,
                "http://www.example.com/perspective",
            )
            self.assertEqual(
                empty_objection.url_reactieformulier, "http://www.config.net/objection"
            )
            self.assertEqual(
                filled_objection.url_reactieformulier,
                "http://www.example.com/objection",
            )

        with self.subTest("Save with url values does not trigger back fill function"):
            new_empty_perspective = InzageProcedureFactory.create(
                url_reactieformulier="",
                beschikbaar_rechtsmiddel=LegalRemedyOptions.perspective,
            )
            new_empty_objection = InzageProcedureFactory.create(
                url_reactieformulier="",
                beschikbaar_rechtsmiddel=LegalRemedyOptions.objection,
            )

            form["perspective_reaction_form_url"] = "http://www.changed.org/perspective"
            form["objection_reaction_form_url"] = "http://www.changed.org/objection"

            with self.captureOnCommitCallbacks(execute=True):
                submit_response = form.submit(name="_save")

            self.assertEqual(submit_response.status_int, 302)

            new_empty_perspective.refresh_from_db()
            new_empty_objection.refresh_from_db()

            self.assertEqual(new_empty_perspective.url_reactieformulier, "")
            self.assertEqual(new_empty_objection.url_reactieformulier, "")
