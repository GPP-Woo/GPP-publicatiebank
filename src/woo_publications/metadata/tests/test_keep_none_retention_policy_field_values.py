from django.test import TestCase

from woo_publications.constants import ArchiveNominationChoices

from ..keep_none_retention_policy_field_values import (
    keep_none_retention_policy_field_values,
)
from ..models import InformationCategory
from .factories import InformationCategoryFactory


class KeepOriginalNoneFixtureInformationCategoryDataTests(TestCase):
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
