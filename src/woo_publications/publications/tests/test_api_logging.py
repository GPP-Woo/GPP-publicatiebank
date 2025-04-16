from datetime import date
from unittest.mock import patch

from django.urls import reverse

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.api.tests.mixins import TokenAuthMixin
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.logging.constants import Events
from woo_publications.logging.models import TimelineLogProxy
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import DocumentActionTypeOptions, PublicationStatusOptions
from ..models import Publication
from .factories import DocumentFactory, PublicationFactory, TopicFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class PublicationLoggingTests(TokenAuthMixin, APITestCase):

    def test_detail_logging(self):
        assert not TimelineLogProxy.objects.exists()
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic],
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = TimelineLogProxy.objects.get()
        expected_data = {
            "event": Events.read,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "_cached_object_repr": "title one",
        }
        self.assertEqual(log.extra_data, expected_data)

    def test_create_logging(self):
        assert not TimelineLogProxy.objects.exists()
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            selectiecategorie="22.1.1",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=10,
            toelichting_bewaartermijn="extra data",
        )
        topic = TopicFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        url = reverse("api:publication-list")
        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [str(topic.uuid)],
            "publicatiestatus": PublicationStatusOptions.concept,
            "publisher": str(organisation.uuid),
            "verantwoordelijke": str(organisation.uuid),
            "opsteller": str(organisation.uuid),
            "officieleTitel": "title one",
            "verkorteTitel": "one",
            "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        }

        with freeze_time("2024-09-24T12:00:00-00:00"):
            response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        log = TimelineLogProxy.objects.get()
        publication = Publication.objects.get()
        expected_data = {
            "event": Events.create,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "object_data": {
                "id": publication.pk,
                "informatie_categorieen": [ic.pk],
                "onderwerpen": [topic.pk],
                "laatst_gewijzigd_datum": "2024-09-24T12:00:00Z",
                "officiele_titel": "title one",
                "omschrijving": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "opsteller": organisation.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "uuid": response.json()["uuid"],
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "one",
                "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "22.1.1",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2034-09-24",
                "toelichting_bewaartermijn": "extra data",
            },
            "_cached_object_repr": "title one",
        }

        self.assertEqual(log.extra_data, expected_data)

    def test_update_publication(self):
        assert not TimelineLogProxy.objects.exists()
        organisation = OrganisationFactory.create(is_actief=True)
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="changed",
            selectiecategorie="changed",
            archiefnominatie=ArchiveNominationChoices.destroy,
            bewaartermijn=10,
            toelichting_bewaartermijn="changed",
        )
        topic = TopicFactory.create()
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic2],
                publicatiestatus=PublicationStatusOptions.concept,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )
        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "onderwerpen": [str(topic.uuid)],
            "publicatiestatus": PublicationStatusOptions.published,
            "publisher": str(organisation.uuid),
            "verantwoordelijke": str(organisation.uuid),
            "opsteller": str(organisation.uuid),
            "officieleTitel": "changed offical title",
            "verkorteTitel": "changed short title",
            "omschrijving": "changed description",
        }

        with freeze_time("2024-09-27T12:00:00-00:00"):
            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = TimelineLogProxy.objects.get()
        expected_data = {
            "event": Events.update,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "object_data": {
                "id": publication.pk,
                "informatie_categorieen": [ic.pk],
                "onderwerpen": [topic.pk],
                "laatst_gewijzigd_datum": "2024-09-27T12:00:00Z",
                "officiele_titel": "changed offical title",
                "omschrijving": "changed description",
                "opsteller": organisation.pk,
                "publicatiestatus": PublicationStatusOptions.published,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "uuid": response.json()["uuid"],
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "changed short title",
                "bron_bewaartermijn": "changed",
                "selectiecategorie": "changed",
                "archiefnominatie": ArchiveNominationChoices.destroy,
                "archiefactiedatum": "2034-09-24",
                "toelichting_bewaartermijn": "changed",
            },
            "_cached_object_repr": "changed offical title",
        }
        self.assertEqual(log.extra_data, expected_data)

    def test_partial_update_publication_status_to_revoked_also_revokes_published_documents(
        self,
    ):
        assert not TimelineLogProxy.objects.exists()
        topic, topic2 = TopicFactory.create_batch(2)
        ic, ic2 = InformationCategoryFactory.create_batch(2)
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-27T00:14:00-00:00"):
            publication = PublicationFactory.create(
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                informatie_categorieen=[ic, ic2],
                onderwerpen=[topic, topic2],
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                selectiecategorie="22.1.1",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum=date(2025, 1, 1),
                toelichting_bewaartermijn="extra data",
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

        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )
        data = {
            "publicatiestatus": PublicationStatusOptions.revoked,
        }

        with freeze_time("2024-09-28T00:14:00-00:00"):
            response = self.client.patch(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        publication.refresh_from_db()
        published_document.refresh_from_db()
        concept_document.refresh_from_db()
        revoked_document.refresh_from_db()

        self.assertEqual(TimelineLogProxy.objects.count(), 2)

        with self.subTest("update publication audit logging"):
            update_publication_log = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
                publication
            ).get(
                extra_data__event=Events.update
            )

            expected_data = {
                "event": Events.update,
                "remarks": "remark",
                "acting_user": {"identifier": "id", "display_name": "username"},
                "object_data": {
                    "id": publication.pk,
                    "informatie_categorieen": [ic.pk, ic2.pk],
                    "onderwerpen": [topic.pk, topic2.pk],
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
                    "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                    "selectiecategorie": "22.1.1",
                    "archiefnominatie": ArchiveNominationChoices.retain,
                    "archiefactiedatum": "2025-01-01",
                    "toelichting_bewaartermijn": "extra data",
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
                "remarks": "remark",
                "acting_user": {"identifier": "id", "display_name": "username"},
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

    def test_destroy_publication(self):
        assert not TimelineLogProxy.objects.exists()
        ic = InformationCategoryFactory.create()
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = PublicationFactory.create(
                informatie_categorieen=[ic],
                publicatiestatus=PublicationStatusOptions.concept,
                publisher=organisation,
                verantwoordelijke=organisation,
                opsteller=organisation,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                bron_bewaartermijn="Selectielijst gemeenten 2020",
                selectiecategorie="22.1.1",
                archiefnominatie=ArchiveNominationChoices.retain,
                archiefactiedatum=date(2025, 1, 1),
                toelichting_bewaartermijn="extra data",
            )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        with freeze_time("2024-09-27T12:00:00-00:00"):
            response = self.client.delete(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        log = TimelineLogProxy.objects.get()
        expected_data = {
            "event": Events.delete,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "object_data": {
                "id": publication.id,
                "informatie_categorieen": [ic.id],
                "onderwerpen": [],
                "laatst_gewijzigd_datum": "2024-09-24T12:00:00Z",
                "officiele_titel": "title one",
                "omschrijving": (
                    "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                ),
                "opsteller": organisation.pk,
                "publicatiestatus": PublicationStatusOptions.concept,
                "publisher": organisation.pk,
                "registratiedatum": "2024-09-24T12:00:00Z",
                "uuid": str(publication.uuid),
                "verantwoordelijke": organisation.pk,
                "verkorte_titel": "one",
                "bron_bewaartermijn": "Selectielijst gemeenten 2020",
                "selectiecategorie": "22.1.1",
                "archiefnominatie": ArchiveNominationChoices.retain,
                "archiefactiedatum": "2025-01-01",
                "toelichting_bewaartermijn": "extra data",
            },
            "_cached_object_repr": "title one",
        }

        self.assertEqual(log.extra_data, expected_data)


class DocumentLoggingTests(TokenAuthMixin, APITestCase):

    def test_detail_logging(self):
        assert not TimelineLogProxy.objects.exists()
        document = DocumentFactory.create(
            officiele_titel="title one",
        )
        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = TimelineLogProxy.objects.get()
        expected_data = {
            "event": Events.read,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "_cached_object_repr": "title one",
        }
        self.assertEqual(log.extra_data, expected_data)

    def test_update_documentation(self):
        assert not TimelineLogProxy.objects.exists()
        publication = PublicationFactory.create()
        with freeze_time("2024-09-27T12:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                publicatiestatus=PublicationStatusOptions.concept,
                identifier="document-1",
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-01-01",
            )

        detail_url = reverse(
            "api:document-detail",
            kwargs={"uuid": str(document.uuid)},
        )

        data = {
            "officieleTitel": "changed officiele_title",
            "verkorteTitel": "changed verkorte_title",
            "omschrijving": "changed omschrijving",
            "publicatiestatus": PublicationStatusOptions.published,
        }

        with freeze_time("2024-09-27T12:00:00-00:00"):
            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = TimelineLogProxy.objects.get()
        expected_data = {
            "event": Events.update,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "object_data": {
                "bestandsformaat": "unknown",
                "bestandsnaam": "unknown.bin",
                "bestandsomvang": 0,
                "creatiedatum": "2024-01-01",
                "document_service": None,
                "document_uuid": None,
                "id": document.pk,
                "identifier": "document-1",
                "laatst_gewijzigd_datum": "2024-09-27T12:00:00Z",
                "lock": "",
                "upload_complete": False,
                "officiele_titel": "changed officiele_title",
                "omschrijving": "changed omschrijving",
                "publicatie": publication.pk,
                "publicatiestatus": PublicationStatusOptions.published,
                "registratiedatum": "2024-09-27T12:00:00Z",
                "soort_handeling": DocumentActionTypeOptions.declared,
                "uuid": str(document.uuid),
                "verkorte_titel": "changed verkorte_title",
            },
            "_cached_object_repr": "changed officiele_title",
        }

        self.assertEqual(log.extra_data, expected_data)

    @patch("woo_publications.publications.api.viewsets.get_client")
    def test_download_logging(self, mock_get_client):
        # mock out the actual download, we don't care about the main result, only about
        # the audit logs
        mock_get_client.return_value.__enter__.return_value.get.return_value.status_code = (
            200
        )
        information_category = InformationCategoryFactory.create()
        document = DocumentFactory.create(
            publicatie__informatie_categorieen=[information_category],
            bestandsomvang=5,
            with_registered_document=True,
        )
        endpoint = reverse("api:document-download", kwargs={"uuid": document.uuid})

        response = self.client.get(endpoint, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = TimelineLogProxy.objects.get()
        self.assertEqual(log.content_object, document)
        expected_data = {
            "event": Events.download,
            "remarks": "remark",
            "acting_user": {"identifier": "id", "display_name": "username"},
            "_cached_object_repr": document.officiele_titel,
        }
        self.assertEqual(log.extra_data, expected_data)
