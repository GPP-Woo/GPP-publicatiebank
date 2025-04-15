from django.test import TestCase

from freezegun import freeze_time

from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.publications.tests.factories import PublicationFactory


class TestPublicationModel(TestCase):

    def test_apply_retention_policy_with_both_archive_nomination_choices(
        self,
    ):
        ic1 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 1",
            selectiecategorie="1.0.1",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="first bewaartermijn",
        )
        ic2 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 2",
            selectiecategorie="1.0.2",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=8,
            toelichting_bewaartermijn="second bewaartermijn",
        )
        ic3 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 3",
            selectiecategorie="1.0.1",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=10,
            toelichting_bewaartermijn="third bewaartermijn",
        )
        ic4 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 2",
            selectiecategorie="1.0.3",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=10,
            toelichting_bewaartermijn="second bewaartermijn",
        )
        ic5 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 4",
            selectiecategorie="1.1.0",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=20,
            toelichting_bewaartermijn="forth bewaartermijn",
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic1, ic2, ic3, ic4, ic5]
            )

        # sanity check that the fields were empty
        self.assertEqual(publication.bron_bewaartermijn, "")
        self.assertEqual(publication.selectiecategorie, "")
        self.assertEqual(publication.archiefnominatie, "")
        self.assertIsNone(publication.archiefactiedatum)
        self.assertEqual(publication.toelichting_bewaartermijn, "")

        publication.apply_retention_policy()

        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn 1")
        self.assertEqual(publication.selectiecategorie, "1.0.1")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(
            str(publication.archiefactiedatum), "2029-09-24"
        )  # 2024-09-24 + 5 years
        self.assertEqual(publication.toelichting_bewaartermijn, "first bewaartermijn")

    def test_apply_retention_policy_with_dispose_archive_nomination_choice(
        self,
    ):
        ic1 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 2",
            selectiecategorie="1.0.3",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=10,
            toelichting_bewaartermijn="second bewaartermijn",
        )
        ic2 = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn 4",
            selectiecategorie="1.1.0",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=20,
            toelichting_bewaartermijn="forth bewaartermijn",
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(informatie_categorieen=[ic1, ic2])

        # sanity check that the fields were empty
        self.assertEqual(publication.bron_bewaartermijn, "")
        self.assertEqual(publication.selectiecategorie, "")
        self.assertEqual(publication.archiefnominatie, "")
        self.assertIsNone(publication.archiefactiedatum)
        self.assertEqual(publication.toelichting_bewaartermijn, "")

        publication.apply_retention_policy()

        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn 4")
        self.assertEqual(publication.selectiecategorie, "1.1.0")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(
            str(publication.archiefactiedatum), "2044-09-24"
        )  # 2024-09-24 + 5 years
        self.assertEqual(publication.toelichting_bewaartermijn, "forth bewaartermijn")
