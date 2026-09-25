import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from woo_publications.config.models import GlobalConfiguration

from ..constants import LegalProcedureOptions
from .factories import InzageProcedureFactory, PublicationFactory


class TestInzageProcedureModelTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(GlobalConfiguration.clear_cache)

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

    def test_set_reactieformulier(self):
        inzage_procedure = InzageProcedureFactory.build()

        with self.subTest("no data"):
            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=None,
                url_reactieformulier=None,
            )
            self.assertEqual(inzage_procedure.url_reactieformulier, "")

        with self.subTest(
            "provide beschikbaar rechtsmiddel with no global config url fields",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
        ):
            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
                url_reactieformulier=None,
            )
            self.assertEqual(inzage_procedure.url_reactieformulier, "")

        with self.subTest(
            "provide beschikbaar rechtsmiddel with no global config url fields",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
        ):
            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
                url_reactieformulier=None,
            )
            self.assertEqual(inzage_procedure.url_reactieformulier, "")

        with self.subTest(
            "provide beschikbaar rechtsmiddel with global config",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
        ):
            config = GlobalConfiguration.get_solo()
            config.perspective_reaction_form_url = "http://www.example.com/perspective"
            config.save()

            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
                url_reactieformulier=None,
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "http://www.example.com/perspective",
            )

        with self.subTest(
            "provide beschikbaar rechtsmiddel with global config",
            beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
        ):
            config = GlobalConfiguration.get_solo()
            config.objection_reaction_form_url = "http://www.example.com/objection"
            config.save()

            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
                url_reactieformulier=None,
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier,
                "http://www.example.com/objection",
            )

        with self.subTest("provide url reactieformulier will always use it."):
            config = GlobalConfiguration.get_solo()
            config.perspective_reaction_form_url = "http://www.example.com/perspective"
            config.objection_reaction_form_url = "http://www.example.com/objection"
            config.save()

            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=LegalProcedureOptions.perspective,
                url_reactieformulier="http://www.important.com/",
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier, "http://www.important.com/"
            )

            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=LegalProcedureOptions.objection,
                url_reactieformulier="http://www.important.com/",
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier, "http://www.important.com/"
            )

            inzage_procedure.set_url_reactieformulier(
                beschikbaar_rechtsmiddel=None,
                url_reactieformulier="http://www.important.com/",
            )
            self.assertEqual(
                inzage_procedure.url_reactieformulier, "http://www.important.com/"
            )
