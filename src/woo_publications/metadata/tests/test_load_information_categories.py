from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from woo_publications.constants import ArchiveNominationChoices

from ..models import InformationCategory
from .factories import InformationCategoryFactory

information_categories_fixture = Path(
    settings.DJANGO_PROJECT_DIR
    / "metadata"
    / "tests"
    / "information_categories_fixture.json",
)


class LoadInformationCategoriesCommandTests(TestCase):
    def test_load_ic_with_empty_db(self):
        assert not InformationCategory.objects.exists()

        call_command(
            "load_information_categories",
            information_categories_fixture,
            stdout=StringIO(),
        )

        self.assertEqual(InformationCategory.objects.count(), 10)

    def test_load_ic_with_random_ics(self):
        assert not InformationCategory.objects.exists()

        InformationCategoryFactory.create_batch(3)

        call_command(
            "load_information_categories",
            information_categories_fixture,
            stdout=StringIO(),
        )

        self.assertEqual(InformationCategory.objects.count(), 13)

    def test_load_updated_none_fixture_ic_fields_stay_the_same(self):
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
        )

        call_command(
            "load_information_categories",
            information_categories_fixture,
            stdout=StringIO(),
        )

        ic.refresh_from_db()
        ic2.refresh_from_db()

        self.assertEqual(InformationCategory.objects.count(), 10)

        for obj in [ic, ic2]:
            self.assertEqual(obj.bron_bewaartermijn, "bewaartermijn")
            self.assertEqual(obj.selectiecategorie, "selectiecategorie")
            self.assertEqual(obj.archiefnominatie, ArchiveNominationChoices.retain)
            self.assertEqual(obj.bewaartermijn, 5)
            self.assertEqual(obj.toelichting_bewaartermijn, "toelichting")
            self.assertEqual(obj.omschrijving, "omschrijving")

    def test_wrong_variable(self):
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'not a file' found."
        ):
            call_command(
                "load_information_categories",
                "not a file",
                stdout=StringIO(),
            )
