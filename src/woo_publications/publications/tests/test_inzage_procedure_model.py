import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from woo_publications.publications.tests.factories import (
    InzageProcedureFactory,
    PublicationFactory,
)


class TestPublicationModel(TestCase):
    def test_start_end_date_constraint(self):
        inzage_procedure = InzageProcedureFactory.build(
            publicatie=PublicationFactory.create()
        )

        with self.subTest("start date before end date"):
            inzage_procedure.datum_begin_inzagetermijn = datetime.date(2020, 2, 2)
            inzage_procedure.datum_einde_inzagetermijn = datetime.date(2020, 12, 2)
            inzage_procedure.save()

        with self.subTest("same dates"):
            inzage_procedure.datum_begin_inzagetermijn = datetime.date(2020, 2, 2)
            inzage_procedure.datum_einde_inzagetermijn = datetime.date(2020, 2, 2)
            inzage_procedure.save()

        with self.subTest("end date before start date"):
            inzage_procedure.datum_begin_inzagetermijn = datetime.date(2020, 12, 2)
            inzage_procedure.datum_einde_inzagetermijn = datetime.date(2020, 2, 2)

            with self.assertRaises(IntegrityError):
                inzage_procedure.save()
