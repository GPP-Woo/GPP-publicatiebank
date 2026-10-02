import uuid
from unittest.mock import MagicMock, patch

from django.contrib import messages
from django.test import TestCase
from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError
from woo_publications.contrib.catalogi_api.typing import IOT
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory

from ..models import GlobalConfiguration
from ..tasks import index_default_iot


class IndexDefaultIOTRegressionTests(TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_iot",
        return_value=IOT(uuid=uuid.uuid4(), url="https://example.com/iot/new"),
    )
    def test_index_default_iot_is_idempotent(self, mock_create_iot: MagicMock):
        """
        the admin schedules this task on every save while
        ``default_iot_url`` is empty. Saving twice before the worker picks it up
        creates two published default IOTs.
        """
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "catalogi_api_service": ServiceFactory.create(
                    for_catalogi_api_docker_compose=True
                ),
                "catalogus_url": "https://example.com/catalogus",
                "default_iot_url": "https://example.com/iot/existing",
            },
        )

        index_default_iot()

        mock_create_iot.assert_not_called()
        self.assertEqual(
            GlobalConfiguration.objects.get().default_iot_url,
            "https://example.com/iot/existing",
        )


@disable_admin_mfa()
class GlobalConfigurationAdminRegressionTests(WebTest):
    url = reverse("admin:config_globalconfiguration_change", args=(1,))

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.documents_service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )
        cls.search_service = ServiceFactory.create(for_gpp_search_docker_compose=True)
        cls.catalogi_service = ServiceFactory.create(
            for_catalogi_api_docker_compose=True
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def _fill_form(self, form):
        form["documents_api_service"] = self.documents_service.pk
        form["organisation_rsin"] = "000000000"
        form["catalogi_api_service"] = self.catalogi_service.pk
        form["gpp_search_service"] = self.search_service.pk
        form["perspective_reaction_form_url"] = "http://www.config.net/perspective"
        form["objection_reaction_form_url"] = "http://www.config.net/objection"

    @patch("woo_publications.config.tasks.index_default_iot.delay")
    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_catalogi",
        side_effect=CatalogiAPIError(message="Catalogus couldn't be created."),
    )
    def test_catalogus_creation_failure_is_reported_to_the_admin(
        self, mock_create_catalogi: MagicMock, mock_index_default_iot: MagicMock
    ):
        """
        The ``CatalogiAPIError`` is swallowed. The admin sees the regular
        success message while ``catalogus_url`` stays empty (and is read-only).
        """
        form = self.app.get(self.url, user=self.user).forms["globalconfiguration_form"]
        self._fill_form(form)

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit(name="_save")

        if response.status_code == 302:
            response = response.follow()
        error_messages = [
            message
            for message in response.context["messages"]
            if message.level == messages.ERROR
        ]
        form_errors = (
            response.context["adminform"].form.errors
            if "adminform" in response.context
            else {}
        )
        self.assertTrue(
            error_messages or form_errors,
            "Catalogus creation failed without any feedback to the admin.",
        )

    @patch("woo_publications.metadata.tasks.index_iot.delay")
    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_catalogi",
        return_value="https://example.com/catalogus",
    )
    @patch("woo_publications.config.tasks.index_default_iot.delay")
    def test_configuring_catalogi_api_indexes_information_categories(
        self,
        mock_index_default_iot: MagicMock,
        mock_create_catalogi: MagicMock,
        mock_index_iot: MagicMock,
    ):
        """
        on a fresh install ``load_information_categories`` runs (from
        ``docker_start.sh``) before the Catalogi API is configured, so all
        ``index_iot`` tasks fail with a non-retried ``RuntimeError``. Configuring the
        Catalogi API afterwards does not schedule them again; only a container
        restart does.
        """
        information_category = InformationCategoryFactory.create(iot_url="")
        form = self.app.get(self.url, user=self.user).forms["globalconfiguration_form"]
        self._fill_form(form)

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        scheduled_ic_ids = [
            call.kwargs.get("information_category_id")
            for call in mock_index_iot.call_args_list
        ]
        self.assertIn(information_category.pk, scheduled_ic_ids)

    @patch(
        "woo_publications.contrib.catalogi_api.client.CatalogiClient.create_catalogi",
        return_value="https://other-openzaak.example.com/catalogussen/new",
    )
    @patch("woo_publications.config.tasks.index_default_iot.delay")
    def test_changing_catalogi_service_does_not_keep_stale_catalogus(
        self, mock_index_default_iot: MagicMock, mock_create_catalogi: MagicMock
    ):
        """
        ``catalogus_url`` / ``default_iot_url`` are only set when empty.
        After switching to another Catalogi API they keep pointing to the old one
        and, being read-only, cannot be corrected in the admin.

        🤷 don't have a clear solution now.
        """
        config = GlobalConfiguration.get_solo()
        config.documents_api_service = self.documents_service
        config.gpp_search_service = self.search_service
        config.catalogi_api_service = self.catalogi_service
        config.catalogus_url = "http://openzaak.docker.internal:8001/catalogussen/old"
        config.default_iot_url = (
            "http://openzaak.docker.internal:8001/informatieobjecttypen/old"
        )
        config.save()
        other_catalogi_service = ServiceFactory.create(
            label="Other Open Zaak catalogi API",
            api_root="https://other-openzaak.example.com/catalogi/api/v1/",
            api_type=self.catalogi_service.api_type,
        )
        form = self.app.get(self.url, user=self.user).forms["globalconfiguration_form"]
        self._fill_form(form)
        form["catalogi_api_service"] = other_catalogi_service.pk

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        config = GlobalConfiguration.objects.get()
        self.assertFalse(
            config.catalogus_url.startswith("http://openzaak.docker.internal"),
            "catalogus_url still points to the previous Catalogi API.",
        )
