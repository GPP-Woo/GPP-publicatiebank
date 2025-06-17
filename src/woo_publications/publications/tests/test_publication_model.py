from datetime import date

from django.db.utils import IntegrityError
from django.test import TestCase

from freezegun import freeze_time

from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.config.models import GlobalConfiguration
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)
from woo_publications.publications.constants import PublicationStatusOptions
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
        assert publication.bron_bewaartermijn == ""
        assert publication.selectiecategorie == ""
        assert publication.archiefnominatie == ""
        assert publication.archiefactiedatum is None
        assert publication.toelichting_bewaartermijn == ""

        publication.apply_retention_policy()

        publication.refresh_from_db()
        # Uses the IC with the lowest
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn 1")
        self.assertEqual(publication.selectiecategorie, "1.0.1")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(
            publication.archiefactiedatum, date(2029, 9, 24)
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
        assert publication.bron_bewaartermijn == ""
        assert publication.selectiecategorie == ""
        assert publication.archiefnominatie == ""
        assert publication.archiefactiedatum is None
        assert publication.toelichting_bewaartermijn == ""

        publication.apply_retention_policy()

        publication.refresh_from_db()
        # uses the IC with the highest year
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn 4")
        self.assertEqual(publication.selectiecategorie, "1.1.0")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(
            publication.archiefactiedatum, date(2044, 9, 24)
        )  # 2024-09-24 + 20 years
        self.assertEqual(publication.toelichting_bewaartermijn, "forth bewaartermijn")

    def test_calculate_gpp_app_publication_url(self):
        config = GlobalConfiguration.get_solo()
        self.addCleanup(GlobalConfiguration.clear_cache)

        with self.subTest("no URL template configured"):
            config.gpp_app_publication_url_template = ""
            config.save()
            publication1 = PublicationFactory.build()

            result = publication1.gpp_app_url

            self.assertEqual(result, "")

        with self.subTest("with URL template configured"):
            config.gpp_app_publication_url_template = (
                "https://example.com/gpp-app/nested/<UUID>/edit"
            )
            config.save()
            publication2 = PublicationFactory.build(
                uuid="771b79e5-3ba7-4fdf-9a89-00a6a5227a8d"
            )

            result = publication2.gpp_app_url

            self.assertEqual(
                result,
                "https://example.com/gpp-app/nested/771b79e5-3ba7-4fdf-9a89-00a6a5227a8d/edit",
            )

    def test_calculate_gpp_burgerportaal_publication_url(self):
        config = GlobalConfiguration.get_solo()
        self.addCleanup(GlobalConfiguration.clear_cache)

        with self.subTest("no URL template configured"):
            config.gpp_burgerportaal_publication_url_template = ""
            config.save()
            publication1 = PublicationFactory.build()

            result = publication1.gpp_burgerportaal_url

            self.assertEqual(result, "")

        with self.subTest("with URL template configured"):
            config.gpp_burgerportaal_publication_url_template = (
                "https://example.com/gpp-burgerportaal/nested/<UUID>/edit"
            )
            config.save()
            publication2 = PublicationFactory.build(
                uuid="771b79e5-3ba7-4fdf-9a89-00a6a5227a8d"
            )

            result = publication2.gpp_burgerportaal_url

            self.assertEqual(
                result,
                "https://example.com/gpp-burgerportaal/nested/771b79e5-3ba7-4fdf-9a89-00a6a5227a8d/edit",
            )

    def test_publisher_constraint(self):
        user = UserFactory.create(superuser=True)
        org_member = OrganisationMemberFactory.create(
            identifier=user.pk,
            naam=user.get_full_name(),
        )
        publisher = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.build(
            eigenaar=org_member, publicatiestatus=PublicationStatusOptions.concept
        )

        with self.subTest("no status with no publisher"):
            publication.publicatiestatus = ""
            publication.publisher = None
            publication.save()

        with self.subTest("no status with publisher"):
            publication.publicatiestatus = ""
            publication.publisher = publisher
            publication.save()

        with self.subTest("concept with no publisher"):
            publication.publicatiestatus = PublicationStatusOptions.concept
            publication.publisher = None
            publication.save()

        with self.subTest("concept with publisher"):
            publication.publicatiestatus = PublicationStatusOptions.concept
            publication.publisher = publisher
            publication.save()

        with self.subTest("published with publisher"):
            publication.publicatiestatus = PublicationStatusOptions.published
            publication.publisher = publisher
            publication.save()

        with self.subTest("published with no publisher (raises errors)"):
            publication.publicatiestatus = PublicationStatusOptions.published
            publication.publisher = None

            with self.assertRaises(IntegrityError):
                publication.save()
