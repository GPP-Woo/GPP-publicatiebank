from django.test import TestCase

from ..keep_organisations_values import keep_organisations_values
from ..models import Organisation
from .factories import OrganisationFactory


class KeepOrganisationsValuesTests(TestCase):
    def test_keep_organisation_values(self):
        assert not Organisation.objects.exists()
        organisation = OrganisationFactory.create(is_actief=True, rsin="000000000")
        organisation2 = OrganisationFactory.create(is_actief=False, rsin="000000000")
        organisation3 = OrganisationFactory.create(is_actief=True, rsin="")
        organisation4 = OrganisationFactory.create(is_actief=False, rsin="")

        with keep_organisations_values():
            Organisation.objects.update(is_actief=False)

        organisation.refresh_from_db()
        organisation2.refresh_from_db()
        organisation3.refresh_from_db()
        organisation4.refresh_from_db()

        self.assertTrue(organisation.is_actief)
        self.assertEqual(organisation.rsin, "000000000")
        self.assertFalse(organisation2.is_actief)
        self.assertEqual(organisation2.rsin, "000000000")
        self.assertTrue(organisation3.is_actief)
        self.assertEqual(organisation3.rsin, "")
        self.assertFalse(organisation4.is_actief)
        self.assertEqual(organisation4.rsin, "")
