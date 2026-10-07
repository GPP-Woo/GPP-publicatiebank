from unittest.mock import MagicMock, patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client
from woo_publications.contrib.catalogi_api.tests.constants import (
    DEFAULT_CATALOGUS,
    DEFAULT_IOT,
)
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.publications.constants import LegalProcedureOptions
from woo_publications.publications.tests.factories import InzageProcedureFactory
from woo_publications.utils.tests.vcr import VCRMixin

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
        "woo_publications.config.tasks.sync_information_categories_and_documents_with_catalog_api.delay"
    )
    def test_update_with_catalogus_urls_filled_out(self, mock_sync_delay: MagicMock):
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
        form["catalogus_url"] = "https://www.example.com/catalogus"
        form["default_iot_url"] = "https://www.example.com/iot"

        with self.captureOnCommitCallbacks(execute=True):
            submit_response = form.submit(name="_save")

        self.assertEqual(submit_response.status_code, 302)
        global_config = GlobalConfiguration.get_solo()
        self.assertEqual(
            global_config.catalogus_url, "https://www.example.com/catalogus"
        )
        self.assertEqual(global_config.default_iot_url, "https://www.example.com/iot")

        mock_sync_delay.assert_not_called()


@disable_admin_mfa()
class GlobalConfigCatalogiTestCase(VCRMixin, TestCase):
    """
    Webtest makes it extremely difficult to interact with django's message framework.
    This is since because we can't acces real requests. Because of this I opted to use
    TestCase for these specific tests.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @patch(
        "woo_publications.config.tasks.sync_information_categories_and_documents_with_catalog_api.delay"
    )
    def test_happy_flow(self, mock_sync_delay: MagicMock):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url,
                {
                    "organisation_rsin": "123456782",
                    "documents_api_service": document_service.pk,
                    "catalogi_api_service": catalogi_service.pk,
                    "gpp_search_service": search_service.pk,
                    "perspective_reaction_form_url": "https://www.config.net/perspective",
                    "objection_reaction_form_url": "https://www.config.net/objection",
                },
            )

        self.assertEqual(response.status_code, 302)
        global_config = GlobalConfiguration.get_solo()
        self.assertNotEqual(global_config.catalogus_url, "")
        self.assertNotEqual(global_config.default_iot_url, "")

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            str(messages[1]),
            _(
                "Catalogi API has been set up successfully. The Information Categories "
                "and Documents will now be processed in the background."
            ),
        )

        with get_client(global_config.catalogi_api_service) as client:
            catalogus_response = client.get(global_config.catalogus_url)
            self.assertEqual(catalogus_response.status_code, 200)

            iot_response = client.get(global_config.default_iot_url)
            self.assertEqual(iot_response.status_code, 200)

        mock_sync_delay.assert_called_with(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )

    @patch(
        "woo_publications.config.tasks.sync_information_categories_and_documents_with_catalog_api.delay"
    )
    def test_happy_flow_catalogi_already_set(self, mock_sync_delay: MagicMock):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url,
                {
                    "organisation_rsin": "100000198",
                    "documents_api_service": document_service.pk,
                    "catalogi_api_service": catalogi_service.pk,
                    "gpp_search_service": search_service.pk,
                    "perspective_reaction_form_url": "https://www.config.net/perspective",
                    "objection_reaction_form_url": "https://www.config.net/objection",
                    "catalogus_url": DEFAULT_CATALOGUS,
                },
            )

        self.assertEqual(response.status_code, 302)
        global_config = GlobalConfiguration.get_solo()
        self.assertEqual(global_config.catalogus_url, DEFAULT_CATALOGUS)
        self.assertNotEqual(global_config.default_iot_url, "")

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            str(messages[1]),
            _(
                "Catalogi API has been set up successfully. The Information Categories "
                "and Documents will now be processed in the background."
            ),
        )

        with get_client(global_config.catalogi_api_service) as client:
            catalogus_response = client.get(global_config.catalogus_url)
            self.assertEqual(catalogus_response.status_code, 200)

            iot_response = client.get(global_config.default_iot_url)
            self.assertEqual(iot_response.status_code, 200)

        mock_sync_delay.assert_called_with(
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
        )

    def test_user_tries_to_set_iot_without_catalogi(self):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url,
                {
                    "organisation_rsin": "000000000",
                    "documents_api_service": document_service.pk,
                    "catalogi_api_service": catalogi_service.pk,
                    "gpp_search_service": search_service.pk,
                    "perspective_reaction_form_url": "https://www.config.net/perspective",
                    "objection_reaction_form_url": "https://www.config.net/objection",
                    "catalogus_url": "",
                    "default_iot_url": DEFAULT_IOT,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["adminform"],
            None,
            _(
                "The default IOT URL field cannot be empty if the Catalogi URL "
                "field is set."
            ),
        )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_catalogi",
        side_effect=CatalogiAPIError(message="some message"),
    )
    def test_creating_catalogus_generates_error(self, mock_create_catalogi: MagicMock):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url,
                {
                    "organisation_rsin": "200000007",
                    "documents_api_service": document_service.pk,
                    "catalogi_api_service": catalogi_service.pk,
                    "gpp_search_service": search_service.pk,
                    "perspective_reaction_form_url": "https://www.config.net/perspective",
                    "objection_reaction_form_url": "https://www.config.net/objection",
                },
            )

        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            str(messages[1]),
            _("Something went wrong while trying to create the Catalogi."),
        )

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        side_effect=CatalogiAPIError(message="some message"),
    )
    def test_creating_iot_generates_error(self, mock_create_iot: MagicMock):
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url,
                {
                    "organisation_rsin": "300000005",
                    "documents_api_service": document_service.pk,
                    "catalogi_api_service": catalogi_service.pk,
                    "gpp_search_service": search_service.pk,
                    "perspective_reaction_form_url": "https://www.config.net/perspective",
                    "objection_reaction_form_url": "https://www.config.net/objection",
                },
            )

        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            str(messages[1]),
            _(
                "Something went wrong while trying to create the default "
                "Informationobjecttypes."
            ),
        )

    @requests_mock.Mocker()
    def test_catalogi_service_not_configured_properly(self, m: requests_mock.Mocker):
        m.post(
            "http://openzaak.docker.internal:8001/catalogi/api/v1/",
            status_code=400,
        )
        document_service = ServiceFactory.create(for_documents_api_docker_compose=True)
        search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        url = reverse("admin:config_globalconfiguration_change", args=(1,))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                url,
                {
                    "organisation_rsin": "300000005",
                    "documents_api_service": document_service.pk,
                    "catalogi_api_service": catalogi_service.pk,
                    "gpp_search_service": search_service.pk,
                    "perspective_reaction_form_url": "https://www.config.net/perspective",
                    "objection_reaction_form_url": "https://www.config.net/objection",
                },
            )

        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            str(messages[1]),
            _(
                "The Catalogi API service is not available. "
                "Because of this the Catalogi and default Informationobjecttypes "
                "couldn't be created. Check if you configured the Service "
                "correctly and make sure that it is running correctly."
            ),
        )
