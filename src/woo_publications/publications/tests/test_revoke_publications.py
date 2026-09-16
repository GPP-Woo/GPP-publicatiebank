import datetime

from django.test import TestCase

from freezegun import freeze_time

from woo_publications.logging.constants import SYSTEM_USER, Events
from woo_publications.logging.models import TimelineLogProxy

from ..constants import PublicationStatusOptions
from ..tasks import revoke_inzage_procedure_publications
from .factories import (
    InzageProcedureFactory,
    PublicationFactory,
)


class TestRevokePublications(TestCase):
    @freeze_time("2026-9-1")
    def test_revoke_inzage_procedure_publications(self):
        # should_revoke
        should_revoke = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        InzageProcedureFactory.create(
            publicatie=should_revoke,
            automatisch_intrekken=True,
            datum_einde_inzagetermijn=datetime.date(2026, 9, 1),
        )
        # should_have_already_been_revoked
        should_have_already_been_revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        InzageProcedureFactory.create(
            publicatie=should_have_already_been_revoked,
            automatisch_intrekken=True,
            datum_einde_inzagetermijn=datetime.date(2026, 1, 1),
        )
        # does_not_automatically_revoke
        does_not_automatically_revoke = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        InzageProcedureFactory.create(
            publicatie=does_not_automatically_revoke,
            automatisch_intrekken=False,
            datum_einde_inzagetermijn=datetime.date(2026, 9, 1),
        )
        # date_does_not_match_today
        date_does_not_match_today = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        InzageProcedureFactory.create(
            publicatie=date_does_not_match_today,
            automatisch_intrekken=True,
            datum_einde_inzagetermijn=datetime.date(2026, 12, 23),
        )
        # concept
        concept = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        InzageProcedureFactory.create(
            publicatie=concept,
            automatisch_intrekken=True,
            datum_einde_inzagetermijn=datetime.date(2026, 9, 1),
        )
        # already_revoked
        already_revoked = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        with freeze_time("2026-1-1"):
            already_revoked.revoke(
                user={"identifier": "unknown", "display_name": "unknown"}
            )
            already_revoked.save()
            InzageProcedureFactory.create(
                publicatie=already_revoked,
                automatisch_intrekken=True,
                datum_einde_inzagetermijn=datetime.date(2026, 9, 1),
            )

        self.assertEqual(TimelineLogProxy.objects.count(), 0)

        # call the task
        with self.captureOnCommitCallbacks(execute=True):
            revoke_inzage_procedure_publications()

        should_revoke.refresh_from_db()
        should_have_already_been_revoked.refresh_from_db()
        does_not_automatically_revoke.refresh_from_db()
        date_does_not_match_today.refresh_from_db()
        concept.refresh_from_db()
        already_revoked.refresh_from_db()

        # should_revoke
        self.assertEqual(
            should_revoke.publicatiestatus, PublicationStatusOptions.revoked
        )
        self.assertEqual(
            should_revoke.ingetrokken_op,
            datetime.datetime(2026, 9, 1, 0, 0, tzinfo=datetime.UTC),
        )
        # should_have_already_been_revoked
        self.assertEqual(
            should_have_already_been_revoked.publicatiestatus,
            PublicationStatusOptions.revoked,
        )
        self.assertEqual(
            should_have_already_been_revoked.ingetrokken_op,
            datetime.datetime(2026, 9, 1, 0, 0, tzinfo=datetime.UTC),
        )
        # does_not_automatically_revoke
        self.assertNotEqual(
            does_not_automatically_revoke.publicatiestatus,
            PublicationStatusOptions.revoked,
        )
        self.assertEqual(does_not_automatically_revoke.ingetrokken_op, None)
        # date_does_not_match_today
        self.assertNotEqual(
            date_does_not_match_today.publicatiestatus, PublicationStatusOptions.revoked
        )
        self.assertEqual(date_does_not_match_today.ingetrokken_op, None)
        # concept
        self.assertNotEqual(concept.publicatiestatus, PublicationStatusOptions.revoked)
        self.assertEqual(concept.ingetrokken_op, None)
        # already revoked. (was already revoked so the status and ingetrokken_op
        # was already set and didn't change)
        self.assertEqual(
            already_revoked.publicatiestatus, PublicationStatusOptions.revoked
        )
        self.assertEqual(
            already_revoked.ingetrokken_op,
            datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.UTC),
        )

        # check that the logging gets created, and that it only gets done for the
        # 'should_revoke' object
        self.assertEqual(TimelineLogProxy.objects.count(), 2)
        timeline_object_1, timeline_object_2 = TimelineLogProxy.objects.order_by("pk")

        expected_data = {
            "event": Events.update,
            "acting_user": {
                "identifier": SYSTEM_USER["identifier"],
                "display_name": SYSTEM_USER["display_name"],
            },
            "object_data": {
                "archiefactiedatum": None,
                "archiefnominatie": "",
                "bron_bewaartermijn": "",
                "datum_begin_geldigheid": None,
                "datum_einde_geldigheid": None,
                "eigenaar": should_revoke.eigenaar.pk,
                "eigenaar_groep": None,
                "gepubliceerd_op": "2026-09-01T00:00:00Z",
                "id": should_revoke.pk,
                "informatie_categorieen": [],
                "ingetrokken_op": "2026-09-01T00:00:00Z",
                "laatst_gewijzigd_datum": "2026-09-01T00:00:00Z",
                "officiele_titel": should_revoke.officiele_titel,
                "omschrijving": "",
                "onderwerpen": [],
                "opsteller": None,
                "publicatiestatus": "ingetrokken",
                "publisher": should_revoke.publisher.pk,
                "registratiedatum": "2026-09-01T00:00:00Z",
                "selectiecategorie": "",
                "toelichting_bewaartermijn": "",
                "uuid": str(should_revoke.uuid),
                "verantwoordelijke": None,
                "verkorte_titel": "",
            },
            "_cached_object_repr": should_revoke.officiele_titel,
        }

        self.assertEqual(timeline_object_1.extra_data, expected_data)

        expected_data = {
            "event": Events.update,
            "acting_user": {
                "identifier": SYSTEM_USER["identifier"],
                "display_name": SYSTEM_USER["display_name"],
            },
            "object_data": {
                "archiefactiedatum": None,
                "archiefnominatie": "",
                "bron_bewaartermijn": "",
                "datum_begin_geldigheid": None,
                "datum_einde_geldigheid": None,
                "eigenaar": should_have_already_been_revoked.eigenaar.pk,
                "eigenaar_groep": None,
                "gepubliceerd_op": "2026-09-01T00:00:00Z",
                "id": should_have_already_been_revoked.pk,
                "informatie_categorieen": [],
                "ingetrokken_op": "2026-09-01T00:00:00Z",
                "laatst_gewijzigd_datum": "2026-09-01T00:00:00Z",
                "officiele_titel": should_have_already_been_revoked.officiele_titel,
                "omschrijving": "",
                "onderwerpen": [],
                "opsteller": None,
                "publicatiestatus": "ingetrokken",
                "publisher": should_have_already_been_revoked.publisher.pk,
                "registratiedatum": "2026-09-01T00:00:00Z",
                "selectiecategorie": "",
                "toelichting_bewaartermijn": "",
                "uuid": str(should_have_already_been_revoked.uuid),
                "verantwoordelijke": None,
                "verkorte_titel": "",
            },
            "_cached_object_repr": should_have_already_been_revoked.officiele_titel,
        }

        self.assertEqual(timeline_object_2.extra_data, expected_data)
