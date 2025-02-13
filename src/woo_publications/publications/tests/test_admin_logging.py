import uuid

from django.urls import reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)
from woo_publications.utils.tests.webtest import add_dynamic_field

from ..constants import DocumentActionTypeOptions, PublicationStatusOptions
from ..models import Document, Publication
from .factories import DocumentFactory, PublicationFactory


@disable_admin_mfa()
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

    def test_admin_create(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        organisation, organisation2 = OrganisationFactory.create_batch(
            2, is_actief=True
        )
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        # Force the value because the select box options get loaded in with js
        form["informatie_categorieen"].force_value([ic.id, ic2.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
        form["publisher"] = str(organisation.pk)
        form["verantwoordelijke"] = str(organisation.pk)
        form["opsteller"] = str(organisation2.pk)
        form["officiele_titel"] = "The official title of this publication"
        form["verkorte_titel"] = "The title"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
            "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur."
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
                "laatst_gewijzigd_datum": "2024-09-25T00:14:00Z",
                "officiele_titel": "The official title of this publication",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur.",
                "opsteller": organisation2.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-25T00:14:00Z",
                "uuid": str(added_item.uuid),
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "The title",
            },
            "_cached_object_repr": "The official title of this publication",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_admin_update(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        organisation, organisation2 = OrganisationFactory.create_batch(
            2, is_actief=True
        )
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
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
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
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
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "officiele_titel": "changed official title",
                    "omschrijving": "changed description",
                    "opsteller": organisation2.pk,
                    "publicatiestatus": PublicationStatusOptions.concept,
                    "publisher": organisation2.pk,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "uuid": str(publication.uuid),
                    "verantwoordelijke": organisation2.pk,
                    "verkorte_titel": "changed short title",
                },
                "_cached_object_repr": "changed official title",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_admin_update_revoke_published_documents_when_revoking_publication(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
            published_document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="http://example.com/1",
                officiele_titel="title",
                creatiedatum="2024-10-17",
            )
            concept_document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.concept,
            )
            revoked_document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.revoked,
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
        concept_document.refresh_from_db()
        revoked_document.refresh_from_db()

        self.assertEqual(TimelineLogProxy.objects.count(), 3)

        with self.subTest("update publication audit logging"):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                publication
            ).get(
                extra_data__event=Events.update
            )

            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": publication.pk,
                    "informatie_categorieen": [ic.pk, ic2.pk],
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "officiele_titel": "title one",
                    "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                    "opsteller": organisation.pk,
                    "publicatiestatus": PublicationStatusOptions.revoked,
                    "publisher": organisation.pk,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "uuid": str(publication.uuid),
                    "verantwoordelijke": organisation.pk,
                    "verkorte_titel": "one",
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
                    "verkorte_titel": "",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "title",
                    "document_service": None,
                    "registratiedatum": "2024-09-27T00:14:00Z",
                    "laatst_gewijzigd_datum": "2024-09-28T00:14:00Z",
                    "soort_handeling": DocumentActionTypeOptions.declared,
                },
                "_cached_object_repr": "title",
            }

            self.assertEqual(update_publication_log.extra_data, expected_data)

    def test_admin_delete(self):
        assert not TimelineLogProxy.objects.exists()
        information_category = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[information_category],
                publicatiestatus=PublicationStatusOptions.concept,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
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
                "laatst_gewijzigd_datum": "2024-09-27T00:14:00Z",
                "officiele_titel": "title one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "opsteller": organisation.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-27T00:14:00Z",
                "uuid": str(publication.uuid),
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "one",
            },
            "_cached_object_repr": "title one",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_admin_inline_update_admin(self):
        assert not TimelineLogProxy.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)

        with freeze_time("2024-09-25T00:14:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic, ic2],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
            document = DocumentFactory.create(publicatie=publication)

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

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
        form["document_set-0-identifier"] = "http://example.com/1"
        form["document_set-0-officiele_titel"] = "title"
        form["document_set-0-creatiedatum"] = "17-10-2024"
        form["document_set-0-publicatiestatus"].select(
            text=PublicationStatusOptions.concept.label
        )

        with freeze_time("2024-09-29T00:14:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        with self.subTest("update inline update logging"):
            log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                document
            ).get()

            expected_data = {
                "event": Events.update,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": document.pk,
                    "lock": "",
                    "upload_complete": False,
                    "uuid": str(document.uuid),
                    "identifier": "http://example.com/1",
                    "publicatie": publication.id,
                    "publicatiestatus": PublicationStatusOptions.concept,
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-10-17",
                    "omschrijving": "",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "verkorte_titel": "",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "title",
                    "document_service": None,
                    "registratiedatum": "2024-09-25T00:14:00Z",
                    "laatst_gewijzigd_datum": "2024-09-25T00:14:00Z",
                    "soort_handeling": DocumentActionTypeOptions.declared,
                },
                "_cached_object_repr": "title",
            }

            self.assertEqual(log.extra_data, expected_data)

    def test_admin_inline_create_admin(self):
        assert not TimelineLogProxy.objects.exists()
        assert not Document.objects.exists()
        ic, ic2 = InformationCategoryFactory.create_batch(2)

        with freeze_time("2024-09-25T00:14:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic, ic2],
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

        form["document_set-TOTAL_FORMS"] = "1"  # we're adding one, dynamically
        add_dynamic_field(
            form, "document_set-0-publicatiestatus", PublicationStatusOptions.concept
        )
        add_dynamic_field(form, "document_set-0-identifier", "http://example.com/1")
        add_dynamic_field(form, "document_set-0-officiele_titel", "title")
        add_dynamic_field(form, "document_set-0-creatiedatum", "17-10-2024")
        add_dynamic_field(form, "document_set-0-bestandsformaat", "application/pdf")
        add_dynamic_field(form, "document_set-0-bestandsnaam", "foo.pdf")
        add_dynamic_field(form, "document_set-0-bestandsomvang", "0")
        add_dynamic_field(
            form,
            "document_set-0-soort_handeling",
            DocumentActionTypeOptions.declared.value,
        )

        with freeze_time("2024-09-26T00:14:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        with self.subTest("update inline update logging"):
            document = Document.objects.get()
            log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                document
            ).get()

            expected_data = {
                "event": Events.create,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": document.pk,
                    "uuid": str(document.uuid),
                    "identifier": "http://example.com/1",
                    "publicatie": publication.id,
                    "publicatiestatus": PublicationStatusOptions.concept,
                    "bestandsnaam": "foo.pdf",
                    "creatiedatum": "2024-10-17",
                    "omschrijving": "",
                    "bestandsomvang": 0,
                    "verkorte_titel": "",
                    "bestandsformaat": "application/pdf",
                    "officiele_titel": "title",
                    "registratiedatum": "2024-09-26T00:14:00Z",
                    "laatst_gewijzigd_datum": "2024-09-26T00:14:00Z",
                    "soort_handeling": DocumentActionTypeOptions.declared,
                    "document_service": None,
                    "document_uuid": None,
                    "lock": "",
                    "upload_complete": False,
                },
                "_cached_object_repr": "title",
            }

            self.assertEqual(log.extra_data, expected_data)

    def test_admin_inline_delete(self):
        assert not TimelineLogProxy.objects.exists()
        information_category = InformationCategoryFactory.create()
        with freeze_time("2024-09-25T00:14:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[information_category],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
            document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.published,
                identifier="document-1",
                officiele_titel="DELETE THIS ITEM",
                verkorte_titel="",
                omschrijving="",
                creatiedatum="2024-09-25",
            )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

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
        form["document_set-0-DELETE"] = True

        with freeze_time("2024-09-29T00:14:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        with self.subTest("update inline update logging"):
            log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                document
            ).get()

            expected_data = {
                "event": Events.delete,
                "acting_user": {
                    "identifier": self.user.id,
                    "display_name": self.user.get_full_name(),
                },
                "object_data": {
                    "id": document.pk,
                    "lock": "",
                    "upload_complete": False,
                    "uuid": str(document.uuid),
                    "identifier": "document-1",
                    "publicatie": publication.id,
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-09-25",
                    "omschrijving": "",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "verkorte_titel": "",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "DELETE THIS ITEM",
                    "publicatiestatus": PublicationStatusOptions.published,
                    "document_service": None,
                    "registratiedatum": "2024-09-25T00:14:00Z",
                    "laatst_gewijzigd_datum": "2024-09-25T00:14:00Z",
                    "soort_handeling": DocumentActionTypeOptions.declared,
                },
                "_cached_object_repr": "DELETE THIS ITEM",
            }

            self.assertEqual(log.extra_data, expected_data)


@disable_admin_mfa()
class TestDocumentAdminAuditLogging(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_document_admin_create(self):
        publication = PublicationFactory.create()
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"

        response = self.app.get(
            reverse("admin:publications_document_add"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatiestatus"] = PublicationStatusOptions.concept
        form["publicatie"] = publication.id
        form["identifier"] = identifier
        form["officiele_titel"] = "The official title of this document"
        form["verkorte_titel"] = "The title"
        form["creatiedatum"] = "2024-01-01"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
            "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur."
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
                "upload_complete": False,
                "uuid": str(added_item.uuid),
                "identifier": identifier,
                "publicatie": publication.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "bestandsnaam": "unknown.bin",
                "creatiedatum": "2024-01-01",
                "omschrijving": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
                    "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur."
                ),
                "document_uuid": None,
                "bestandsomvang": 0,
                "verkorte_titel": "The title",
                "bestandsformaat": "unknown",
                "officiele_titel": "The official title of this document",
                "document_service": None,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-24T12:00:00Z",
                "soort_handeling": DocumentActionTypeOptions.declared,
            },
            "_cached_object_repr": "The official title of this document",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_document_admin_update(self):
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        publication = PublicationFactory.create()
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatiestatus"] = PublicationStatusOptions.concept
        form["publicatie"] = publication.id
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
                    "upload_complete": False,
                    "uuid": str(document.uuid),
                    "identifier": identifier,
                    "publicatie": publication.pk,
                    "publicatiestatus": PublicationStatusOptions.concept,
                    "bestandsnaam": "unknown.bin",
                    "creatiedatum": "2024-11-11",
                    "omschrijving": "changed description",
                    "document_uuid": None,
                    "bestandsomvang": 0,
                    "verkorte_titel": "changed short title",
                    "bestandsformaat": "unknown",
                    "officiele_titel": "changed official title",
                    "document_service": None,
                    "registratiedatum": "2024-09-25T14:00:00Z",
                    "laatst_gewijzigd_datum": "2024-09-29T14:00:00Z",
                    "soort_handeling": DocumentActionTypeOptions.declared,
                },
                "_cached_object_repr": "changed official title",
            }

            self.assertEqual(update_log.extra_data, expected_data)

    def test_document_admin_delete(self):
        publication = PublicationFactory.create()
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                publicatie=publication,
                identifier=identifier,
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
                "upload_complete": False,
                "uuid": str(document.uuid),
                "identifier": identifier,
                "publicatie": publication.pk,
                "publicatiestatus": PublicationStatusOptions.published,
                "bestandsnaam": "unknown.bin",
                "creatiedatum": "2024-11-11",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "document_uuid": None,
                "bestandsomvang": 0,
                "verkorte_titel": "one",
                "bestandsformaat": "unknown",
                "officiele_titel": "title one",
                "document_service": None,
                "registratiedatum": "2024-09-25T14:00:00Z",
                "laatst_gewijzigd_datum": "2024-09-25T14:00:00Z",
                "soort_handeling": DocumentActionTypeOptions.declared,
            },
            "_cached_object_repr": "title one",
        }

        self.assertEqual(log.extra_data, expected_data)
