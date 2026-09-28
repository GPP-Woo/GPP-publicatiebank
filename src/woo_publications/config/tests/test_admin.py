"""
Configuration admin (smoke)tests.
"""

from unittest.mock import MagicMock, patch

from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import LegalProcedureOptions
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
            beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
        )
        filled_perspective = InzageProcedureFactory.create(
            url_reactieformulier="http://www.example.com/perspective",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
        )
        empty_objection = InzageProcedureFactory.create(
            url_reactieformulier="",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
        )
        filled_objection = InzageProcedureFactory.create(
            url_reactieformulier="http://www.example.com/objection",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
        )
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)

        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        response = self.app.get(url, user=self.user)

        form = response.forms["globalconfiguration_form"]

        with self.subTest("Save with empty url values triggers back fill function"):
            form["documents_api_service"] = document_service.pk
            form["organisation_rsin"] = "000000000"
            form["catalogi_api_service"] = catalogi_service.pk
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
                beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
            )
            new_empty_objection = InzageProcedureFactory.create(
                url_reactieformulier="",
                beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
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

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_catalogi",
        return_value="https://example.com/catalogi",
    )
    @patch("woo_publications.config.tasks.index_default_iot.delay")
    def test_saving_model_tries_to_create_category_and_triggers_task(
        self, mock_index_default_iot_delay: MagicMock, mock_create_catalogi: MagicMock
    ):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)

        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        response = self.app.get(url, user=self.user)

        form = response.forms["globalconfiguration_form"]

        form["documents_api_service"] = document_service.pk
        form["organisation_rsin"] = "000000000"
        form["catalogi_api_service"] = catalogi_service.pk
        form["gpp_search_service"] = search_service.pk
        form["perspective_reaction_form_url"] = "http://www.config.net/perspective"
        form["objection_reaction_form_url"] = "http://www.config.net/objection"

        with self.captureOnCommitCallbacks(execute=True):
            submit_response = form.submit(name="_save")

        self.assertEqual(submit_response.status_code, 302)
        global_config = GlobalConfiguration.objects.get()
        self.assertEqual(global_config.catalogus_url, "https://example.com/catalogi")
        mock_index_default_iot_delay.assert_called_once()

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_catalogi",
        side_effect=CatalogiAPIError(message="some error", status_code=None),
    )
    def test_saving_model_and_catalogi_api_raises_error_field_is_not_set(
        self, mock_create_catalogi: MagicMock
    ):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)

        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        response = self.app.get(url, user=self.user)

        form = response.forms["globalconfiguration_form"]

        form["documents_api_service"] = document_service.pk
        form["organisation_rsin"] = "000000000"
        form["catalogi_api_service"] = catalogi_service.pk
        form["gpp_search_service"] = search_service.pk
        form["perspective_reaction_form_url"] = "http://www.config.net/perspective"
        form["objection_reaction_form_url"] = "http://www.config.net/objection"

        with self.captureOnCommitCallbacks(execute=True):
            submit_response = form.submit(name="_save")

        self.assertEqual(submit_response.status_code, 302)
        global_config = GlobalConfiguration.objects.get()
        self.assertEqual(global_config.catalogus_url, "")
