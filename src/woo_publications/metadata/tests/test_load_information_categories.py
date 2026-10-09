import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.contrib.tests.factories import ServiceFactory

from ..models import InformationCategory
from .factories import InformationCategoryFactory

information_categories_fixture = Path(
    settings.DJANGO_PROJECT_DIR
    / "metadata"
    / "tests"
    / "information_categories_fixture.json",
)


class LoadInformationCategoriesCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        catalogi_service = ServiceFactory.create(for_catalogi_api_docker_compose=True)
        config = GlobalConfiguration.get_solo()
        config.documents_api_service = ServiceFactory.create(
            for_documents_api_docker_compose=True
        )
        config.organisation_rsin = "000000000"
        # state right after upgrading: no catalogi API configured
        config.catalogi_api_service = catalogi_service
        config.save()

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    @patch("woo_publications.metadata.tasks.index_iot.delay")
    def test_load_ic_with_empty_db(self, mock_index_iot_delay: MagicMock):
        assert not InformationCategory.objects.exists()

        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "load_information_categories",
                information_categories_fixture,
                stdout=StringIO(),
            )

        self.assertEqual(InformationCategory.objects.count(), 10)
        self.assertEqual(mock_index_iot_delay.call_count, 10)

    @patch("woo_publications.metadata.tasks.index_iot.delay")
    def test_load_ic_with_random_ics(self, mock_index_iot_delay: MagicMock):
        assert not InformationCategory.objects.exists()

        InformationCategoryFactory.create_batch(3)

        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "load_information_categories",
                information_categories_fixture,
                stdout=StringIO(),
            )

        self.assertEqual(InformationCategory.objects.count(), 13)
        self.assertEqual(mock_index_iot_delay.call_count, 13)

    @patch("woo_publications.metadata.tasks.index_iot.delay")
    def test_load_without_catalogi_api(self, mock_index_iot_delay: MagicMock):
        config = GlobalConfiguration.get_solo()
        config.catalogi_api_service = None
        config.save()

        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "load_information_categories",
                information_categories_fixture,
                stdout=StringIO(),
            )

        self.assertEqual(mock_index_iot_delay.call_count, 0)

    @patch("woo_publications.metadata.tasks.index_iot.delay")
    def test_load_updated_none_fixture_ic_fields_stay_the_same(
        self, mock_index_iot_delay: MagicMock
    ):
        assert not InformationCategory.objects.exists()

        ic = InformationCategoryFactory.create(
            order=1010,
            uuid="be4e21c2-0be5-4616-945e-1f101b0c0e6d",
            identifier="https://identifier.overheid.nl/tooi/def/thes/kern/c_139c6280",
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
            omschrijving="omschrijving",
            iot_uuid="5171900e-3b15-426e-979a-8e0fa76c5a77",
            iot_url="https://www.example.com/",
        )
        ic2 = InformationCategoryFactory.create(
            order=1020,
            uuid="8f3bdef0-a926-4f67-b1f2-94c583c462ce",
            identifier="https://identifier.overheid.nl/tooi/def/thes/kern/c_aab6bfc7",
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
            omschrijving="omschrijving",
            iot_uuid="5171900e-3b15-426e-979a-8e0fa76c5a77",
            iot_url="https://www.example.com/",
        )

        with self.captureOnCommitCallbacks(execute=True):
            call_command(
                "load_information_categories",
                information_categories_fixture,
                stdout=StringIO(),
            )

        ic.refresh_from_db()
        ic2.refresh_from_db()

        self.assertEqual(InformationCategory.objects.count(), 10)
        # check that if iot fields are set that the task won't get called
        self.assertEqual(mock_index_iot_delay.call_count, 8)

        for obj in [ic, ic2]:
            self.assertEqual(obj.bron_bewaartermijn, "bewaartermijn")
            self.assertEqual(obj.selectiecategorie, "selectiecategorie")
            self.assertEqual(obj.archiefnominatie, ArchiveNominationChoices.retain)
            self.assertEqual(obj.bewaartermijn, 5)
            self.assertEqual(obj.toelichting_bewaartermijn, "toelichting")
            self.assertEqual(obj.omschrijving, "omschrijving")
            self.assertEqual(
                obj.iot_uuid, uuid.UUID("5171900e-3b15-426e-979a-8e0fa76c5a77")
            )
            self.assertEqual(obj.iot_url, "https://www.example.com/")

    def test_wrong_variable(self):
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'not a file' found."
        ):
            call_command(
                "load_information_categories",
                "not a file",
                stdout=StringIO(),
            )
