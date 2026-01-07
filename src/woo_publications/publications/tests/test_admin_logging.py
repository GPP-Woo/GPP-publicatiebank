import tempfile
import uuid

from django.test import override_settings
from django.urls import reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from webtest import Upload

from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from ..models import Document, Publication, Topic
from .factories import TEST_IMG_PATH, DocumentFactory, PublicationFactory, TopicFactory


@disable_admin_mfa()
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestPublicationAdminAuditLogging(WebTest):
    """
    Test that CRUD actions on publications are audit-logged.

    We have a generic implementation in woo_publications.logging for this behaviour,
    for which the code coverage is provided through this test class.

    Additionally, there's a system check to ensure audit logging is added to our admin
    classes, which should cover the rest of the apps/models.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_admin_create(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            selectiecategorie="20.1.2",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn="2",
            toelichting_bewaartermijn="extra data",
        )
        topic = TopicFactory.create()
        organisation, organisation2 = OrganisationFactory.create_batch(
            2, is_actief=True
        )
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        # Force the value because the select box options get loaded in with js
        form["informatie_categorieen"].force_value([ic.pk, ic2.pk])
        form["onderwerpen"].force_value([topic.pk])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["publisher"] = str(organisation.pk)
        form["verantwoordelijke"] = str(organisation.pk)
        form["opsteller"] = str(organisation2.pk)
        form["officiele_titel"] = "The official title of this publication"
        form["verkorte_titel"] = "The title"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
            "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
            "eleifend eros sed consectetur."
        )

        with freeze_time("2024-09-25T00:14:00-00:00"):
            form.submit(name="_save")

        added_item = Publication.objects.get()
        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.create,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": added_item.pk,
                "informatie_categorieen": [ic.pk, ic2.pk],
                "onderwerpen": [topic.pk],
                "eigenaar": self.organisation_member.pk,
                "eigenaar_groep": None,
                "laatst_gewijzigd_datum": "2024-09-25T00:14:00Z",
                "officiele_titel": "The official title of this publication",
                "omschrijving": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris "
                    "risus nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris "
                    "interdum eleifend eros sed consectetur."
                ),
                "opsteller": organisation2.pk,
                "publicatiestatus": PublicationStatusOptions.published,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-25T00:14:00Z",
                "uuid": str(added_item.uuid),
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "The title",
                "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "20.1.2",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2026-09-25",
                "toelichting_bewaartermijn": "extra data",
                "datum_begin_geldigheid": None,
                "datum_einde_geldigheid": None,
                "gepubliceerd_op": "2024-09-25T00:14:00Z",
                "ingetrokken_op": None,
            },
            "_cached_object_repr": "The official title of this publication",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_admin_update(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            selectiecategorie="20.1.2",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=10,
            toelichting_bewaartermijn="extra data",
        )
        topic, topic2 = TopicFactory.create_batch(2)
        organisation, organisation2 = OrganisationFactory.create_batch(
            2, is_actief=True
        )
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                onderwerpen=[topic, topic2],
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.concept,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].select_multiple(texts=[ic.naam])
        form["onderwerpen"].select_multiple(texts=[topic.officiele_titel])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["publisher"] = str(organisation2.pk)
        form["verantwoordelijke"] = str(organisation2.pk)
        form["opsteller"] = str(organisation2.pk)
        form["officiele_titel"] = "changed official title"
        form["verkorte_titel"] = "changed short title"
        form["omschrijving"] = "changed description"

        with freeze_time("2024-09-28T00:14:00-00:00"):
            form.submit(name="_save")

        publication.refresh_from_db()

        self.assertEqual(TimelineLogProxy.objects.count(), 2)
        read_log, update_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("read audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": "title one",
            }

            self.assertEqual(read_log.extra_data, expected_data)

        with self.subTest("update audit logging"):
            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": publication.pk,
                    "informatie_categorieen": [ic.pk],
                    "onderwerpen": [topic.pk],
                    "eigenaar": self.organisation_member.pk,
                    "eigenaar_groep": None,
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "officiele_titel": "changed official title",
                    "omschrijving": "changed description",
                    "opsteller": organisation2.pk,
                    "publicatiestatus": PublicationStatusOptions.published,
                    "publisher": organisation2.pk,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "uuid": str(publication.uuid),
                    "verantwoordelijke": organisation2.pk,
                    "verkorte_titel": "changed short title",
                    "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                    "selectiecategorie": "20.1.2",
                    "archiefnominatie": ArchiveNominationChoices.retain,
                    "archiefactiedatum": "2034-09-28",
                    "toelichting_bewaartermijn": "extra data",
                    "datum_begin_geldigheid": None,
                    "datum_einde_geldigheid": None,
                    "gepubliceerd_op": "2024-09-28T00:14:00Z",
                    "ingetrokken_op": None,
                },
                "_cached_object_repr": "changed official title",
            }
            self.assertEqual(update_log.extra_data, expected_data)

    def test_admin_update_revoke_documents_when_revoking_publication(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        topic = TopicFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                onderwerpen=[topic],
                eigenaar=self.organisation_member,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
            published_document = DocumentFactory.create(
                publicatie=publication,
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="http://example.com/1",
                officiele_titel="title",
                creatiedatum="2024-10-17",
            )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TimelineLogProxy.objects.count(), 1)

        with self.subTest("read audit logging"):
            log = TimelineLogProxy.objects.get()

            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": "title one",
            }

            self.assertEqual(log.extra_data, expected_data)

        form = response.forms["publication_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.revoked.label)

        with freeze_time("2024-09-28T00:14:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        publication.refresh_from_db()
        published_document.refresh_from_db()

        self.assertEqual(TimelineLogProxy.objects.count(), 3)

        with self.subTest("update publication audit logging"):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                publication
            ).get(extra_data__event=Events.update)

            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": publication.pk,
                    "informatie_categorieen": [ic.pk, ic2.pk],
                    "onderwerpen": [topic.pk],
                    "eigenaar": self.organisation_member.pk,
                    "eigenaar_groep": None,
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "officiele_titel": "title one",
                    "omschrijving": "Lorem ipsum dolor sit amet, "
                    "consectetur adipiscing elit.",
                    "opsteller": organisation.pk,
                    "publicatiestatus": PublicationStatusOptions.revoked,
                    "publisher": organisation.pk,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "uuid": str(publication.uuid),
                    "verantwoordelijke": organisation.pk,
                    "verkorte_titel": "one",
                    "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                    "selectiecategorie": "",
                    "archiefnominatie": ArchiveNominationChoices.retain,
                    "archiefactiedatum": "2025-01-01",
                    "toelichting_bewaartermijn": "",
                    "datum_begin_geldigheid": None,
                    "datum_einde_geldigheid": None,
                    "gepubliceerd_op": "2024-09-27T00:14:00Z",
                    "ingetrokken_op": "2024-09-28T00:14:00Z",
                },
                "_cached_object_repr": "title one",
            }

            self.assertEqual(update_publication_log.extra_data, expected_data)

        with self.subTest("update published document audit logging"):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                published_document
            ).get()

            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": published_document.pk,
                    "lock": "",
                    "eigenaar": self.organisation_member.pk,
                    "upload_complete": False,
                    "uuid": str(published_document.uuid),
                    "identifier": "http://example.com/1",
                    "publicatie": publication.id,
                    "publicatiestatus": PublicationStatusOptions.revoked,
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-10-17",
                    "omschrijving": "",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "source_url": "",
                    "verkorte_titel": "",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "title",
                    "document_service": None,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "ontvangstdatum": None,
                    "datum_ondertekend": None,
                    "gepubliceerd_op": "2024-09-27T00:14:00Z",
                    "ingetrokken_op": "2024-09-28T00:14:00Z",
                },
                "_cached_object_repr": "title",
            }

            self.assertEqual(update_publication_log.extra_data, expected_data)

    def test_publication_revoke_action_log(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        topic = TopicFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                onderwerpen=[topic],
                eigenaar=self.organisation_member,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
                publicatiestatus=PublicationStatusOptions.published,
            )
            published_document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.published,
                eigenaar=self.organisation_member,
                identifier="http://example.com/1",
                officiele_titel="title",
                creatiedatum="2024-10-17",
            )

        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )
        self.assertEqual(changelist.status_code, 200)

        form = changelist.forms["changelist-form"]
        form["_selected_action"] = [publication.pk]
        form["action"] = "revoke"

        with freeze_time("2024-09-28T00:14:00-00:00"):
            form.submit()

        self.assertEqual(TimelineLogProxy.objects.count(), 2)

        with self.subTest("update publication audit logging"):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                publication
            ).get(extra_data__event=Events.update)

            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": publication.pk,
                    "informatie_categorieen": [ic.pk, ic2.pk],
                    "onderwerpen": [topic.pk],
                    "eigenaar": self.organisation_member.pk,
                    "eigenaar_groep": None,
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "officiele_titel": "title one",
                    "omschrijving": "Lorem ipsum dolor sit amet, "
                    "consectetur adipiscing elit.",
                    "opsteller": organisation.pk,
                    # updated to revoked
                    "publicatiestatus": PublicationStatusOptions.revoked,
                    "publisher": organisation.pk,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "datum_begin_geldigheid": None,
                    "datum_einde_geldigheid": None,
                    "gepubliceerd_op": "2024-09-27T00:14:00Z",
                    "ingetrokken_op": "2024-09-28T00:14:00Z",
                    "uuid": str(publication.uuid),
                    "verantwoordelijke": organisation.pk,
                    "verkorte_titel": "one",
                    "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                    "selectiecategorie": "",
                    "archiefnominatie": ArchiveNominationChoices.retain,
                    "archiefactiedatum": "2025-01-01",
                    "toelichting_bewaartermijn": "",
                },
                "_cached_object_repr": "title one",
            }

            self.assertEqual(update_publication_log.extra_data, expected_data)

        with self.subTest("update document audit logging"):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                published_document
            ).get()

            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": published_document.pk,
                    "lock": "",
                    "eigenaar": self.organisation_member.pk,
                    "upload_complete": False,
                    "uuid": str(published_document.uuid),
                    "identifier": "http://example.com/1",
                    "publicatie": publication.id,
                    # updated to revoked
                    "publicatiestatus": PublicationStatusOptions.revoked,
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-10-17",
                    "omschrijving": "",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "source_url": "",
                    "verkorte_titel": "",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "title",
                    "document_service": None,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "ontvangstdatum": None,
                    "datum_ondertekend": None,
                    "gepubliceerd_op": "2024-09-27T00:14:00Z",
                    "ingetrokken_op": "2024-09-28T00:14:00Z",
                },
                "_cached_object_repr": "title",
            }

            self.assertEqual(update_publication_log.extra_data, expected_data)

    def test_admin_delete(self):
        assert not TimelineLogProxy.objects.exists()
        information_category = InformationCategoryFactory.create()
        topic = TopicFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[information_category],
                onderwerpen=[topic],
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.concept,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum="2025-01-01",
            )
        reverse_url = reverse(
            "admin:publications_publication_delete",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.delete,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": publication.pk,
                "informatie_categorieen": [information_category.pk],
                "onderwerpen": [topic.pk],
                "eigenaar": self.organisation_member.pk,
                "eigenaar_groep": None,
                "laatst_gewijzigd_datum": "2024-09-27T00:14:00Z",
                "officiele_titel": "title one",
                "omschrijving": "Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.",
                "opsteller": organisation.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-27T00:14:00Z",
                "uuid": str(publication.uuid),
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "one",
                "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2025-01-01",
                "toelichting_bewaartermijn": "",
                "datum_begin_geldigheid": None,
                "datum_einde_geldigheid": None,
                "gepubliceerd_op": None,
                "ingetrokken_op": None,
            },
            "_cached_object_repr": "title one",
        }

        self.assertEqual(log.extra_data, expected_data)


@disable_admin_mfa()
class TestDocumentAdminAuditLogging(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_document_admin_create(self):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"

        response = self.app.get(
            reverse("admin:publications_document_add"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatie"] = publication.id
        form["identifier"] = identifier
        form["officiele_titel"] = "The official title of this document"
        form["verkorte_titel"] = "The title"
        form["creatiedatum"] = "2024-01-01"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
            "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
            "eleifend eros sed consectetur."
        )

        with freeze_time("2024-09-24T12:00:00-00:00"):
            form.submit(name="_save")

        added_item = Document.objects.get()
        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.create,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": added_item.pk,
                "lock": "",
                "eigenaar": self.organisation_member.pk,
                "upload_complete": False,
                "uuid": str(added_item.uuid),
                "identifier": identifier,
                "publicatie": publication.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "bestandsnaam": "unknown.bin",
                "creatiedatum": "2024-01-01",
                "omschrijving": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris "
                    "risus nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris "
                    "interdum eleifend eros sed consectetur."
                ),
                "document_uuid": None,
                "bestandsomvang": 0,
                "source_url": "",
                "verkorte_titel": "The title",
                "bestandsformaat": "unknown",
                "officiele_titel": "The official title of this document",
                "document_service": None,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-24T12:00:00Z",
                "ontvangstdatum": None,
                "datum_ondertekend": None,
                "gepubliceerd_op": None,
                "ingetrokken_op": None,
            },
            "_cached_object_repr": "The official title of this document",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_document_admin_update(self):
        publication = PublicationFactory.create()
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                eigenaar=self.organisation_member,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatiestatus"] = PublicationStatusOptions.published
        form["identifier"] = identifier
        form["officiele_titel"] = "changed official title"
        form["verkorte_titel"] = "changed short title"
        form["creatiedatum"] = "2024-11-11"
        form["omschrijving"] = "changed description"

        with freeze_time("2024-09-29T14:00:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TimelineLogProxy.objects.count(), 2)

        document.refresh_from_db()

        read_log, update_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("read audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": "title one",
            }

            self.assertEqual(read_log.extra_data, expected_data)

        with self.subTest("update audit logging"):
            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": document.pk,
                    "lock": "",
                    "eigenaar": self.organisation_member.pk,
                    "upload_complete": False,
                    "uuid": str(document.uuid),
                    "identifier": identifier,
                    "publicatie": publication.pk,
                    "publicatiestatus": PublicationStatusOptions.published,
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-11-11",
                    "omschrijving": "changed description",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "source_url": "",
                    "verkorte_titel": "changed short title",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "changed official title",
                    "document_service": None,
                    "registratiedatum": "2024-09-25T14:00:00Z",
                    "laatst_gewijzigd_datum": "2024-09-29T14:00:00Z",
                    "ontvangstdatum": None,
                    "datum_ondertekend": None,
                    "gepubliceerd_op": "2024-09-25T14:00:00Z",
                    "ingetrokken_op": None,
                },
                "_cached_object_repr": "changed official title",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_document_revoke_action_update_log(self):
        publication = PublicationFactory.create()
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                identifier=identifier,
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-11-11",
            )

        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [document.pk]
        form["action"] = "revoke"

        with freeze_time("2024-09-29T14:00:00-00:00"):
            form.submit(name="_save")

        with self.subTest("update audit logging"):
            update_log = TimelineLogProxy.objects.get()
            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": document.pk,
                    "lock": "",
                    "eigenaar": self.organisation_member.pk,
                    "upload_complete": False,
                    "uuid": str(document.uuid),
                    "identifier": identifier,
                    "publicatie": publication.pk,
                    "publicatiestatus": PublicationStatusOptions.revoked,  # updated
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-11-11",
                    "omschrijving": "Lorem ipsum dolor sit amet, "
                    "consectetur adipiscing elit.",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "source_url": "",
                    "verkorte_titel": "one",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "title one",
                    "document_service": None,
                    "registratiedatum": "2024-09-25T14:00:00Z",
                    "laatst_gewijzigd_datum": "2024-09-29T14:00:00Z",
                    "ontvangstdatum": None,
                    "datum_ondertekend": None,
                    "gepubliceerd_op": "2024-09-25T14:00:00Z",
                    "ingetrokken_op": "2024-09-29T14:00:00Z",
                },
                "_cached_object_repr": "title one",
            }
            self.assertEqual(update_log.extra_data, expected_data)

    def test_document_change_owner_log(self):
        publication = PublicationFactory.create()
        org_member_1 = OrganisationMemberFactory.create(
            naam="test-naam", identifier="test-identifier"
        )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                identifier=identifier,
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-11-11",
            )

        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]
        form["_selected_action"] = [document.pk]
        form["action"] = "change_owner"

        response = form.submit()

        self.assertEqual(response.status_code, 200)

        confirmation_form = response.forms[1]
        confirmation_form["eigenaar"].select(text=str(org_member_1))

        with freeze_time("2024-09-29T14:00:00-00:00"):
            confirmation_form.submit()

        update_log = TimelineLogProxy.objects.get()
        expected_data = {
            "event": Events.update,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": document.pk,
                "lock": "",
                "eigenaar": org_member_1.pk,  # updated
                "upload_complete": False,
                "uuid": str(document.uuid),
                "identifier": identifier,
                "publicatie": publication.pk,
                "publicatiestatus": PublicationStatusOptions.published,
                "bestandsnaam": "unknown.bin",
                "creatiedatum": "2024-11-11",
                "omschrijving": "Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.",
                "document_uuid": None,
                "bestandsomvang": 0,
                "source_url": "",
                "verkorte_titel": "one",
                "bestandsformaat": "unknown",
                "officiele_titel": "title one",
                "document_service": None,
                "registratiedatum": "2024-09-25T14:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-29T14:00:00Z",
                "ontvangstdatum": None,
                "datum_ondertekend": None,
                "gepubliceerd_op": "2024-09-25T14:00:00Z",
                "ingetrokken_op": None,
            },
            "_cached_object_repr": "title one",
        }
        self.assertEqual(update_log.extra_data, expected_data)

    def test_document_admin_delete(self):
        publication = PublicationFactory.create()
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                identifier=identifier,
                eigenaar=self.organisation_member,
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-11-11",
            )
        reverse_url = reverse(
            "admin:publications_document_delete",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.delete,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": document.pk,
                "lock": "",
                "eigenaar": self.organisation_member.pk,
                "upload_complete": False,
                "uuid": str(document.uuid),
                "identifier": identifier,
                "publicatie": publication.pk,
                "publicatiestatus": PublicationStatusOptions.published,
                "bestandsnaam": "unknown.bin",
                "creatiedatum": "2024-11-11",
                "omschrijving": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                ),
                "document_uuid": None,
                "bestandsomvang": 0,
                "source_url": "",
                "verkorte_titel": "one",
                "bestandsformaat": "unknown",
                "officiele_titel": "title one",
                "document_service": None,
                "registratiedatum": "2024-09-25T14:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-25T14:00:00Z",
                "datum_ondertekend": None,
                "ontvangstdatum": None,
                "ingetrokken_op": None,
                "gepubliceerd_op": "2024-09-25T14:00:00Z",
            },
            "_cached_object_repr": "title one",
        }
        self.assertEqual(log.extra_data, expected_data)


@disable_admin_mfa()
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestTopicAdminAuditLogging(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_topic_admin_log_create(self):
        with open(TEST_IMG_PATH, "rb") as infile:
            upload = Upload("test.jpeg", infile.read(), "image/jpeg")

        reverse_url = reverse("admin:publications_topic_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["topic_form"]
        form["afbeelding"] = upload
        form["officiele_titel"] = "Lorem Ipsum"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
        )
        form["publicatiestatus"] = PublicationStatusOptions.published
        form["promoot"] = False

        with freeze_time("2024-09-24T12:00:00-00:00"):
            form.submit(name="_save")

        added_item = Topic.objects.get()
        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.create,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": added_item.pk,
                "uuid": str(added_item.uuid),
                "afbeelding": added_item.afbeelding.name,
                "officiele_titel": "Lorem Ipsum",
                "omschrijving": "Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.published,
                "promoot": False,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-24T12:00:00Z",
            },
            "_cached_object_repr": "Lorem Ipsum",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_topic_admin_log_update(self):
        with open(TEST_IMG_PATH, "rb") as infile:
            upload = Upload("test.jpeg", infile.read(), "image/jpeg")

        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic = TopicFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
            )

        reverse_url = reverse(
            "admin:publications_topic_change",
            kwargs={"object_id": topic.pk},
        )
        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["topic_form"]
        form["afbeelding"] = upload
        form["officiele_titel"] = "changed official title"
        form["omschrijving"] = "changed description"
        form["publicatiestatus"] = PublicationStatusOptions.revoked
        form["promoot"] = True

        with freeze_time("2024-09-27T12:00:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TimelineLogProxy.objects.count(), 2)

        topic.refresh_from_db()

        read_log, update_log = TimelineLogProxy.objects.order_by("pk")

        with self.subTest("read audit logging"):
            expected_data = {
                "event": Events.read,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "_cached_object_repr": "title one",
            }

            self.assertEqual(read_log.extra_data, expected_data)

        with self.subTest("update audit logging"):
            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": topic.pk,
                    "uuid": str(topic.uuid),
                    "afbeelding": topic.afbeelding.name,
                    "officiele_titel": "changed official title",
                    "omschrijving": "changed description",
                    "publicatiestatus": PublicationStatusOptions.revoked,
                    "promoot": True,
                    "registratiedatum": "2024-09-24T12:00:00Z",
                    "laatst_gewijzigd_datum": "2024-09-27T12:00:00Z",
                },
                "_cached_object_repr": "changed official title",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_topic_revoke_action_update_log(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic = TopicFactory.create(
                officiele_titel="Lorem Ipsum",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                publicatiestatus=PublicationStatusOptions.published,
                promoot=True,
            )

        changelist = self.app.get(
            reverse("admin:publications_topic_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [topic.pk]
        form["action"] = "revoke"

        with freeze_time("2024-09-29T14:00:00-00:00"):
            form.submit(name="_save")

        with self.subTest("update audit logging"):
            update_log = TimelineLogProxy.objects.get()
            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": topic.pk,
                    "uuid": str(topic.uuid),
                    "afbeelding": topic.afbeelding.name,
                    "officiele_titel": "Lorem Ipsum",
                    "omschrijving": "Lorem ipsum dolor sit amet, "
                    "consectetur adipiscing elit.",
                    "publicatiestatus": PublicationStatusOptions.revoked,  # updated
                    "promoot": True,
                    "registratiedatum": "2024-09-24T12:00:00Z",
                    "laatst_gewijzigd_datum": "2024-09-29T14:00:00Z",
                },
                "_cached_object_repr": "Lorem Ipsum",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_topic_admin_log_delete(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            topic = TopicFactory.create(
                officiele_titel="Lorem Ipsum",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                publicatiestatus=PublicationStatusOptions.published,
                promoot=True,
            )

        reverse_url = reverse(
            "admin:publications_topic_delete",
            kwargs={"object_id": topic.pk},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]
        response = form.submit()

        self.assertEqual(response.status_code, 302)

        log = TimelineLogProxy.objects.get()

        expected_data = {
            "event": Events.delete,
            "acting_user": {
                "identifier": self.user.id,
                "display_name": self.user.get_full_name(),
            },
            "object_data": {
                "id": topic.pk,
                "uuid": str(topic.uuid),
                "afbeelding": topic.afbeelding.name,
                "officiele_titel": "Lorem Ipsum",
                "omschrijving": "Lorem ipsum dolor sit amet, "
                "consectetur adipiscing elit.",
                "publicatiestatus": PublicationStatusOptions.published,
                "promoot": True,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-24T12:00:00Z",
            },
            "_cached_object_repr": "Lorem Ipsum",
        }
        self.assertEqual(log.extra_data, expected_data)
