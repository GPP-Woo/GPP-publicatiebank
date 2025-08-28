import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from woo_publications.accounts.models import OrganisationMember
from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.contrib.documents_api.client import DocumentsAPIError

from ..constants import PublicationStatusOptions
from ..models import Document
from .factories import DocumentFactory, PublicationFactory


@disable_admin_mfa()
class TestDocumentAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def assertNumResults(self, response, amount: int):
        self.assertContains(response, "field-bestandsnaam", amount)

    def assertDocumentListed(self, response, document: Document, times: int = 1):
        # check for record presence by counting how many times the detail/change link is
        # present
        detail_path = reverse("admin:publications_document_change", args=(document.pk,))
        self.assertContains(response, detail_path, times)

    def test_document_admin_shows_items(self):
        DocumentFactory.create(
            eigenaar=self.organisation_member,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        DocumentFactory.create(
            eigenaar=self.organisation_member,
            officiele_titel="title two",
            verkorte_titel="two",
            omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
            "facilisis mollis urna.",
        )

        response = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-bestandsnaam", 2)

    def test_document_admin_search(self):
        publication = PublicationFactory.create()
        publication2 = PublicationFactory.create()
        org_member_1 = OrganisationMemberFactory.create(
            identifier="test-identifier",
            naam="test-naam",
        )
        with freeze_time("2024-09-24T12:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
                eigenaar=org_member_1,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                identifier="document-1",
                bestandsnaam="doc1.txt",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document2 = DocumentFactory.create(
                publicatie=publication2,
                eigenaar=self.organisation_member,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                identifier="document-2",
                bestandsnaam="doc2.txt",
            )
        reverse_url = reverse("admin:publications_document_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter on uuid"):
            form["q"] = str(publication.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document)

        with self.subTest("filter on officiele_titel"):
            form["q"] = "title one"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document)

        with self.subTest("filter on verkorte_titel"):
            form["q"] = "two"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document2)

        with self.subTest("filter on bestandsnaam"):
            form["q"] = "doc2.txt"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document2)

        with self.subTest("filter on publication uuid"):
            form["q"] = str(publication.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document)

        with self.subTest("filter on owner identifier"):
            form["q"] = org_member_1.identifier
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document)

    def test_document_admin_list_filters(self):
        self.app.set_user(user=self.user)
        with freeze_time("2024-09-24T12:00:00-00:00"):
            DocumentFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                eigenaar=self.organisation_member,
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-09-24",
                identifier="document-1",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document2 = DocumentFactory.create(
                publicatie__publicatiestatus=PublicationStatusOptions.concept,
                publicatiestatus=PublicationStatusOptions.concept,
                eigenaar=self.organisation_member,
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, "
                "facilisis mollis urna.",
                creatiedatum="2024-09-25",
                identifier="document-2",
            )
        reverse_url = reverse("admin:publications_document_changelist")

        with freeze_time("2024-09-25T00:14:00-00:00"):
            response = self.app.get(reverse_url)

        self.assertEqual(response.status_code, 200)

        with self.subTest("filter on registratiedatum"):
            search_response = response.click(description=_("Today"), index=0)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on registratiedatum
            assert "registratiedatum__gte" in search_response.context["request"].GET

            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document2)

        with self.subTest("filter on creatiedatum"):
            search_response = response.click(description=_("Today"), index=1)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on creatiedatum
            assert "creatiedatum__gte" in search_response.context["request"].GET

            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document2)

        with self.subTest("filter on publicatiestatus"):
            search_response = response.click(
                description=str(PublicationStatusOptions.concept.label)
            )

            self.assertEqual(search_response.status_code, 200)

            self.assertEqual(search_response.status_code, 200)
            self.assertNumResults(search_response, 1)
            self.assertDocumentListed(search_response, document2)

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_document_admin_create(self):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept
        )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"

        response = self.app.get(
            reverse("admin:publications_document_add"),
            user=self.user,
        )

        form = response.forms["document_form"]

        with self.subTest("documenthandeling fields save default values"):
            form["publicatie"] = publication.id
            form["identifier"] = identifier
            form["officiele_titel"] = "The official title of this document"
            form["verkorte_titel"] = "The title"
            form["creatiedatum"] = "2024-01-01"
            form["omschrijving"] = (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur.",
            )

            add_response = form.submit(name="_save")

            self.assertRedirects(
                add_response, reverse("admin:publications_document_changelist")
            )
            added_item = Document.objects.order_by("-pk").first()
            assert added_item is not None
            # test if defaults will be saved
            self.assertEqual(
                added_item.publicatiestatus, PublicationStatusOptions.concept
            )
            self.assertEqual(added_item.eigenaar, self.organisation_member)

        with self.subTest("complete data"):
            form["eigenaar"].select(text=str(self.organisation_member))
            form["publicatie"] = publication.id
            form["identifier"] = identifier
            form["officiele_titel"] = "The official title of this document"
            form["verkorte_titel"] = "The title"
            form["creatiedatum"] = "2024-01-01"
            form["ontvangstdatum_0"] = "2024-09-24"
            form["ontvangstdatum_1"] = "14:00:00"
            form["datum_ondertekend_0"] = "2024-09-24"
            form["datum_ondertekend_1"] = "14:00:00"
            form["omschrijving"] = (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur.",
            )

            add_response = form.submit(name="_save")

            self.assertRedirects(
                add_response, reverse("admin:publications_document_changelist")
            )
            added_item = Document.objects.order_by("-pk").first()
            assert added_item is not None

            self.assertEqual(
                added_item.publicatiestatus, PublicationStatusOptions.concept
            )
            self.assertEqual(added_item.eigenaar, self.organisation_member)
            self.assertEqual(added_item.publicatie, publication)
            self.assertEqual(added_item.identifier, identifier)
            self.assertEqual(
                added_item.officiele_titel, "The official title of this document"
            )
            self.assertEqual(added_item.verkorte_titel, "The title")
            self.assertEqual(
                added_item.omschrijving,
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
                "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
                "eleifend eros sed consectetur.",
            )
            self.assertEqual(
                str(added_item.ontvangstdatum), "2024-09-24 12:00:00+00:00"
            )
            self.assertEqual(
                str(added_item.datum_ondertekend), "2024-09-24 12:00:00+00:00"
            )
            self.assertEqual(
                str(added_item.registratiedatum), "2024-09-24 12:00:00+00:00"
            )
            self.assertEqual(
                str(added_item.laatst_gewijzigd_datum), "2024-09-24 12:00:00+00:00"
            )

    def test_document_admin_revoked_publication_not_present_in_dropdown(self):
        PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.concept, officiele_titel="concept"
        )
        PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="published",
        )

        # cannot create a revoked publication directly
        revoked_publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="revoked",
        )
        revoked_publication.publicatiestatus = PublicationStatusOptions.revoked
        revoked_publication.save()

        response = self.app.get(
            reverse("admin:publications_document_add"),
            user=self.user,
        )

        form = response.forms["document_form"]
        # create a list of all the dropdown labels
        publicatie_labels = [publicatie[2] for publicatie in form["publicatie"].options]

        self.assertIn("concept", publicatie_labels)
        self.assertIn("published", publicatie_labels)
        self.assertNotIn("revoked", publicatie_labels)

    @patch("woo_publications.publications.admin.index_document.delay")
    def test_document_create_schedules_index_task(
        self, mock_index_document_delay: MagicMock
    ):
        publication = PublicationFactory.create(
            publicatiestatus=PublicationStatusOptions.published
        )
        identifier = f"https://www.openzaak.nl/documenten/{str(uuid.uuid4())}"

        response = self.app.get(
            reverse("admin:publications_document_add"),
            user=self.user,
        )

        form = response.forms["document_form"]
        form["publicatie"] = publication.id
        form["identifier"] = identifier
        form["officiele_titel"] = "The official title of this document"
        form["verkorte_titel"] = "The title"
        form["creatiedatum"] = "2024-01-01"
        form["omschrijving"] = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus "
            "nibh, iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum "
            "eleifend eros sed consectetur.",
        )

        with self.captureOnCommitCallbacks(execute=True):
            add_response = form.submit(name="_save")

        self.assertRedirects(
            add_response, reverse("admin:publications_document_changelist")
        )
        added_item = Document.objects.order_by("-pk").first()
        assert added_item is not None
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(added_item.uuid)}
        )
        mock_index_document_delay.assert_called_once_with(
            document_id=added_item.pk,
            download_url=f"http://testserver{download_url}",
        )

    def test_document_admin_update(self):
        org_member_1 = OrganisationMemberFactory(
            identifier="test-identifier",
            naam="test-naam",
        )
        publication = PublicationFactory.create()
        with freeze_time("2024-09-25T14:00:00-00:00"):
            document = DocumentFactory.create(
                publicatie=publication,
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

        # assert that publicatie isn't editable after creation
        self.assertNotIn("publicatie", form.fields)

        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["eigenaar"].force_value([org_member_1.pk])
        form["identifier"] = identifier
        form["officiele_titel"] = "changed official title"
        form["verkorte_titel"] = "changed short title"
        form["omschrijving"] = "changed description"

        with freeze_time("2024-09-29T14:00:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        document.refresh_from_db()
        self.assertEqual(document.publicatiestatus, PublicationStatusOptions.published)
        self.assertEqual(document.eigenaar, org_member_1)
        self.assertEqual(document.publicatie, publication)
        self.assertEqual(document.identifier, identifier)
        self.assertEqual(document.officiele_titel, "changed official title")
        self.assertEqual(document.verkorte_titel, "changed short title")
        self.assertEqual(document.omschrijving, "changed description")
        self.assertEqual(str(document.registratiedatum), "2024-09-25 14:00:00+00:00")
        self.assertEqual(
            str(document.laatst_gewijzigd_datum), "2024-09-29 14:00:00+00:00"
        )

    @patch("woo_publications.publications.admin.index_document.delay")
    def test_document_update_schedules_index_task(
        self, mock_index_document_delay: MagicMock
    ):
        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(document.uuid)}
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["officiele_titel"] = "changed official title"

        with self.captureOnCommitCallbacks(execute=True):
            update_response = form.submit(name="_save")

        self.assertRedirects(
            update_response, reverse("admin:publications_document_changelist")
        )

        mock_index_document_delay.assert_called_once_with(
            document_id=document.pk,
            download_url=f"http://testserver{download_url}",
        )

    def test_document_cannot_update_when_revoked(self):
        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        self.assertNotIn("officiele_titel", form.fields)

        response = form.submit(name="_save", expect_errors=True)

        self.assertEqual(response.status_code, 403)

    @patch("woo_publications.publications.admin.remove_document_from_index.delay")
    def test_document_update_schedules_remove_from_index_task(
        self, mock_remove_document_from_index_delay: MagicMock
    ):
        document = DocumentFactory.create(
            uuid="82687820-90f2-4c6d-a73b-2e1201a3a76a",
            publicatiestatus=PublicationStatusOptions.published,
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["publicatiestatus"] = PublicationStatusOptions.revoked

        with self.captureOnCommitCallbacks(execute=True):
            update_response = form.submit(name="_save")

        self.assertRedirects(
            update_response, reverse("admin:publications_document_changelist")
        )

        mock_remove_document_from_index_delay.assert_called_once_with(
            document_id=document.pk
        )

    @patch(
        "woo_publications.publications.admin.remove_document_from_documents_api.delay"
    )
    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_document_admin_delete(
        self,
        mock_remove_from_index_by_uuid_delay: MagicMock,
        mock_remove_document_from_documents_api: MagicMock,
    ):
        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            with_registered_document=True,
        )
        reverse_url = reverse(
            "admin:publications_document_delete",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]

        with patch(
            "woo_publications.contrib.documents_api.client.DocumentenClient.destroy_document",
            side_effect=DocumentsAPIError(message="error"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Document.objects.filter(identifier=document.identifier).exists()
        )
        mock_remove_from_index_by_uuid_delay.assert_called_once_with(
            model_name="Document",
            uuid=str(document.uuid),
        )
        mock_remove_document_from_documents_api.assert_called_once_with(
            document_id=document.id,
            user_id=self.user.pk,
            service_uuid=document.document_service.uuid,
            document_uuid=document.document_uuid,
        )

    @patch(
        "woo_publications.publications.admin.remove_document_from_documents_api.delay"
    )
    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_document_admin_delete_unpublished(
        self,
        mock_remove_from_index_by_uuid_delay: MagicMock,
        mock_remove_document_from_documents_api: MagicMock,
    ):
        document = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked
        )
        reverse_url = reverse(
            "admin:publications_document_delete",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)
        form = response.forms[1]

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit()

        self.assertEqual(response.status_code, 302)
        mock_remove_from_index_by_uuid_delay.assert_not_called()
        mock_remove_document_from_documents_api.assert_not_called()

    def test_document_admin_service_select_box_only_displays_document_apis(self):
        service = ServiceFactory.create(
            api_root="https://example.com/",
            api_type=APITypes.drc,
        )
        ServiceFactory.create(
            api_root="https://foo.com/",
            api_type=APITypes.zrc,
        )

        response = self.app.get(
            reverse("admin:publications_document_add"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        document_select = form["document_service"]

        self.assertEqual(len(document_select.options), 2)

        # test that default and document service are selectable but the zaak service
        # isn't
        service_option_values = [option[0] for option in document_select.options]
        self.assertEqual(service_option_values, ["", str(service.pk)])

    @patch("woo_publications.publications.admin.index_document.delay")
    def test_index_bulk_action(self, mock_index_document_delay: MagicMock):
        published_doc = DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
        )
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
        )
        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        download_url = reverse(
            "api:document-download", kwargs={"uuid": str(published_doc.uuid)}
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Document.objects.all()]
        form["action"] = "sync_to_index"
        with self.captureOnCommitCallbacks(execute=True):
            form.submit()

        mock_index_document_delay.assert_called_once_with(
            document_id=published_doc.pk,
            download_url=f"http://testserver{download_url}",
        )

    @patch("woo_publications.publications.admin.remove_document_from_index.delay")
    def test_remove_from_index_bulk_action(
        self, mock_remove_document_from_index_delay: MagicMock
    ):
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
        )
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
        )
        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Document.objects.all()]
        form["action"] = "remove_from_index"
        with self.captureOnCommitCallbacks(execute=True):
            form.submit()

        for doc_id in Document.objects.values_list("pk", flat=True):
            mock_remove_document_from_index_delay.assert_any_call(
                document_id=doc_id, force=True
            )

    @patch(
        "woo_publications.publications.admin.remove_document_from_documents_api.delay"
    )
    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_bulk_removal_action(
        self,
        mock_remove_from_index_by_uuid_delay: MagicMock,
        mock_remove_document_from_documents_api: MagicMock,
    ):
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
        )
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
        )
        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Document.objects.all()]
        form["action"] = "delete_selected"

        response = form.submit()

        with self.captureOnCommitCallbacks(execute=True):
            confirmation_form = response.forms[1]
            confirmation_form.submit()

        for doc_uuid in Document.objects.values_list("uuid", flat=True):
            mock_remove_from_index_by_uuid_delay.assert_any_call(
                model_name="Document", uuid=doc_uuid, force=True
            )
        mock_remove_document_from_documents_api.assert_not_called()

    @patch(
        "woo_publications.publications.admin.remove_document_from_documents_api.delay"
    )
    @patch("woo_publications.publications.admin.remove_from_index_by_uuid.delay")
    def test_bulk_removal_action_with_service_triggers_task(
        self,
        mock_remove_from_index_by_uuid_delay: MagicMock,
        mock_remove_document_from_documents_api: MagicMock,
    ):
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.published,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
            with_registered_document=True,
        )
        DocumentFactory.create(
            publicatiestatus=PublicationStatusOptions.revoked,
            publicatie__publicatiestatus=PublicationStatusOptions.published,
            with_registered_document=True,
        )
        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Document.objects.all()]
        form["action"] = "delete_selected"

        response = form.submit()

        with patch(
            "woo_publications.contrib.documents_api.client.DocumentenClient.destroy_document",
            side_effect=DocumentsAPIError(message="error"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                confirmation_form = response.forms[1]
                confirmation_form.submit()

        for doc in Document.objects.all():
            mock_remove_from_index_by_uuid_delay.assert_any_call(
                model_name="Document", uuid=doc.uuid, force=True
            )
            mock_remove_document_from_documents_api.assert_called_once_with(
                document_id=doc.id,
                user_id=self.user.pk,
                service_uuid=doc.document_service.uuid,
                document_uuid=doc.document_uuid,
            )

    @patch("woo_publications.publications.admin.remove_document_from_index.delay")
    def test_document_revoke_action(
        self,
        mock_remove_document_from_index_delay: MagicMock,
    ):
        published_document = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.published,
            publicatiestatus=PublicationStatusOptions.published,
        )
        concept_document = DocumentFactory.create(
            publicatie__publicatiestatus=PublicationStatusOptions.concept,
            publicatiestatus=PublicationStatusOptions.concept,
        )
        revoked_document = DocumentFactory.create(
            publicatie__revoked=True,
            publicatiestatus=PublicationStatusOptions.revoked,
        )

        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [doc.pk for doc in Document.objects.all()]
        form["action"] = "revoke"

        with self.captureOnCommitCallbacks(execute=True):
            form.submit()

        published_document.refresh_from_db()
        concept_document.refresh_from_db()
        revoked_document.refresh_from_db()

        self.assertEqual(mock_remove_document_from_index_delay.call_count, 2)
        self.assertEqual(
            revoked_document.publicatiestatus, PublicationStatusOptions.revoked
        )
        for doc in [published_document, concept_document]:
            self.assertEqual(doc.publicatiestatus, PublicationStatusOptions.revoked)
            mock_remove_document_from_index_delay.assert_any_call(
                document_id=doc.pk, force=True
            )

    def test_change_owner_action(self):
        org_member_1 = OrganisationMemberFactory.create(
            naam="test-naam", identifier="test-identifier"
        )
        doc1 = DocumentFactory.create(eigenaar=self.organisation_member)
        doc2 = DocumentFactory.create(eigenaar=self.organisation_member)
        changelist = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )

        form = changelist.forms["changelist-form"]
        form["_selected_action"] = [doc1.pk, doc2.pk]
        form["action"] = "change_owner"

        response = form.submit()

        self.assertEqual(response.status_code, 200)

        with self.subTest("no data supplied"):
            confirmation_form = response.forms[1]

            error_response = confirmation_form.submit()
            self.assertFormError(
                error_response.context["form"],
                None,
                _("You need to provide a valid 'owner' or 'identifier' and 'name'."),
            )

        with self.subTest("only identifier supplied"):
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].force_value([])
            confirmation_form["identifier"] = "admin@admin.admin"
            confirmation_form["naam"] = ""

            error_response = confirmation_form.submit()

            self.assertFormError(
                error_response.context["form"], "naam", _("This field is required.")
            )

        with self.subTest("only naam supplied"):
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].force_value([])
            confirmation_form["identifier"] = ""
            confirmation_form["naam"] = "admin@admin.admin"

            error_response = confirmation_form.submit()

            self.assertFormError(
                error_response.context["form"],
                "identifier",
                _("This field is required."),
            )

        with self.subTest("identifier and naam supplied"):
            self.assertFalse(
                OrganisationMember.objects.filter(
                    identifier="admin@admin.admin", naam="admin"
                ).exists()
            )
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].force_value([])
            confirmation_form["identifier"] = "admin@admin.admin"
            confirmation_form["naam"] = "admin"
            confirmation_form.submit()

            doc1.refresh_from_db()
            doc2.refresh_from_db()

            self.assertEqual(response.status_code, 200)

            org_member_2 = OrganisationMember.objects.get(
                identifier="admin@admin.admin", naam="admin"
            )

            self.assertEqual(doc1.eigenaar, org_member_2)
            self.assertEqual(doc2.eigenaar, org_member_2)

        with self.subTest("eigenaar supplied"):
            confirmation_form = response.forms[1]
            confirmation_form["eigenaar"].select(text=str(org_member_1))
            confirmation_form["identifier"] = ""
            confirmation_form["naam"] = ""

            confirmation_form.submit()

            doc1.refresh_from_db()
            doc2.refresh_from_db()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(doc1.eigenaar, org_member_1)
            self.assertEqual(doc2.eigenaar, org_member_1)
