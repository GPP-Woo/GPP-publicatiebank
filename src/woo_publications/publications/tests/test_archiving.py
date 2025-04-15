from django.test import TestCase

from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.models import InformationCategory
from woo_publications.metadata.tests.factories import InformationCategoryFactory

from ..archiving import get_retention_informatie_category


class GetRetentionInformationCategoryTest(TestCase):
    def test_with_both_archive_nomination_choices_always_return_retains(self):
        assert InformationCategory.DoesNotExist()
        InformationCategoryFactory.create_batch(
            5, archiefnominatie=ArchiveNominationChoices.destroy
        )
        InformationCategoryFactory.create_batch(
            5, archiefnominatie=ArchiveNominationChoices.retain
        )

        ic_queryset = InformationCategory.objects.all()
        ic = get_retention_informatie_category(ic_queryset)

        assert ic
        self.assertEqual(ic.archiefnominatie, ArchiveNominationChoices.retain)

    def test_archive_nomination_retain_returns_lowest_bewaartermijn(self):
        assert InformationCategory.DoesNotExist()
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.retain, bewaartermijn=10
        )
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.retain, bewaartermijn=20
        )
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.retain, bewaartermijn=7
        )
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.retain, bewaartermijn=25
        )

        ic_queryset = InformationCategory.objects.all()
        ic = get_retention_informatie_category(ic_queryset)

        assert ic
        self.assertEqual(ic.bewaartermijn, 7)

    def test_archive_nomination_dispose_returns_highest_bewaartermijn(self):
        assert InformationCategory.DoesNotExist()
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.destroy, bewaartermijn=10
        )
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.destroy, bewaartermijn=20
        )
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.destroy, bewaartermijn=7
        )
        InformationCategoryFactory.create(
            archiefnominatie=ArchiveNominationChoices.destroy, bewaartermijn=25
        )

        ic_queryset = InformationCategory.objects.all()
        ic = get_retention_informatie_category(ic_queryset)

        assert ic
        self.assertEqual(ic.bewaartermijn, 25)

    def test_empty_qs_results_in_none(self):
        assert InformationCategory.DoesNotExist()

        ic_queryset = InformationCategory.objects.all()
        ic = get_retention_informatie_category(ic_queryset)

        self.assertIsNone(ic)
