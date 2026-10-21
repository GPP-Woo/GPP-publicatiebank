import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.config.models import GlobalConfiguration
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.contrib.catalogi_api.tests.constants import (
    DEFAULT_CATALOGUS,
    DEFAULT_IOT,
)
from woo_publications.contrib.tests.factories import ServiceFactory

from ..keep_none_retention_policy_field_values import (
    keep_none_retention_policy_field_values,
)
from ..models import InformationCategory
from .factories import InformationCategoryFactory


class KeepOriginalNoneFixtureInformationCategoryDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        service = cls.service = ServiceFactory.create(
            for_catalogi_api_docker_compose=True
        )
        GlobalConfiguration.objects.update_or_create(
            pk=GlobalConfiguration.singleton_instance_id,
            defaults={
                "catalogi_api_service": service,
                "catalogus_url": DEFAULT_CATALOGUS,
                "default_iot_url": DEFAULT_IOT,
            },
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

    def test_keep_none_retention_policy_field_values(self):
        assert not InformationCategory.objects.exists()
        InformationCategoryFactory.create_batch(
            10,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
            omschrijving="omschrijving",
        )

        with keep_none_retention_policy_field_values():
            InformationCategory.objects.update(
                bron_bewaartermijn="",
                selectiecategorie="",
                archiefnominatie=ArchiveNominationChoices.destroy,
                bewaartermijn=10,
                toelichting_bewaartermijn="",
                omschrijving="",
            )

        for obj in InformationCategory.objects.iterator():
            self.assertEqual(obj.bron_bewaartermijn, "bewaartermijn")
            self.assertEqual(obj.selectiecategorie, "selectiecategorie")
            self.assertEqual(obj.archiefnominatie, ArchiveNominationChoices.retain)
            self.assertEqual(obj.bewaartermijn, 5)
            self.assertEqual(obj.toelichting_bewaartermijn, "toelichting")
            self.assertEqual(obj.omschrijving, "omschrijving")

    @patch("woo_publications.metadata.tasks.index_iot.delay")
    def test_sync_with_oz(self, mock_index_iot_delay: MagicMock):
        assert not InformationCategory.objects.exists()
        ic = InformationCategoryFactory.create()

        with (
            self.captureOnCommitCallbacks(execute=True),
            keep_none_retention_policy_field_values(),
        ):
            InformationCategory.objects.update(naam="updated name")

        mock_index_iot_delay.assert_called_with(
            information_category_id=ic.pk,
            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
        )

    @patch("woo_publications.metadata.tasks.update_iot_description.delay")
    def test_updated_name_updates_iot(
        self, mock_update_iot_description_delay: MagicMock
    ):
        assert not InformationCategory.objects.exists()
        ic_uuid = uuid.uuid4()
        ic = InformationCategoryFactory.create(
            iot_url=f"{self.service.api_root}/{ic_uuid}",
            iot_uuid=ic_uuid,
        )

        with (
            self.captureOnCommitCallbacks(execute=True),
            keep_none_retention_policy_field_values(),
        ):
            InformationCategory.objects.update(naam="updated name")

        mock_update_iot_description_delay.assert_called_with(
            information_category_id=ic.pk
        )
