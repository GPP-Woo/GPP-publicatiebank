import uuid

from django.urls import reverse
from django.utils.translation import gettext as _

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from zgw_consumers.constants import APITypes
from zgw_consumers.test.factories import ServiceFactory

from woo_publications.accounts.tests.factories import UserFactory

from ..models import Document
from .factories import DocumentFactory, PublicationFactory


@disable_admin_mfa()
class TestDocumentAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_document_admin_shows_items(self):
        DocumentFactory.create(
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        )
        DocumentFactory.create(
            officiele_titel="title two",
            verkorte_titel="two",
            omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
        )

        response = self.app.get(
            reverse("admin:publications_document_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-identifier", 2)

    def test_document_admin_search(self):
        with freeze_time("2024-09-24T12:00:00-00:00"):
            publication = DocumentFactory.create(
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            publication2 = DocumentFactory.create(
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
            )
        reverse_url = reverse("admin:publications_document_changelist")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("filter_on_identifier"):
            form["q"] = publication.identifier

            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-identifier", 1)
            # searchbar + object
            self.assertContains(search_response, publication.identifier)
            self.assertNotContains(search_response, publication2.identifier)

        with self.subTest("filter_on_officiele_title"):
            form["q"] = "title one"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, publication.identifier, 1)

        with self.subTest("filter_on_verkorte_titel"):
            form["q"] = "two"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, publication2.identifier, 1)

        with self.subTest("filter_on_verkorte_titel"):
            form["q"] = str(publication.identifier)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, "title one", 1)

    def test_document_admin_list_filters(self):
        self.app.set_user(user=self.user)

        with freeze_time("2024-09-24T12:00:00-00:00"):
            DocumentFactory.create(
                officiele_titel="title one",
                verkorte_titel="one",
                omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                creatiedatum="2024-09-24",
            )
        with freeze_time("2024-09-25T12:30:00-00:00"):
            document2 = DocumentFactory.create(
                officiele_titel="title two",
                verkorte_titel="two",
                omschrijving="Vestibulum eros nulla, tincidunt sed est non, facilisis mollis urna.",
                creatiedatum="2024-09-25",
            )
        reverse_url = reverse("admin:publications_document_changelist")

        with freeze_time("2024-09-25T00:14:00-00:00"):
            response = self.app.get(reverse_url)

        self.assertEqual(response.status_code, 200)

        with self.subTest("filter_on_registratiedatum"):
            search_response = response.click(description=_("Today"), index=0)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on registratiedatum
            assert "registratiedatum__gte" in search_response.context["request"].GET

            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, document2.identifier, 1)

        with self.subTest("filter_on_creatiedatum"):
            search_response = response.click(description=_("Today"), index=1)

            self.assertEqual(search_response.status_code, 200)

            # Sanity check that we indeed filtered on creatiedatum
            assert "creatiedatum__gte" in search_response.context["request"].GET

            self.assertContains(search_response, "field-identifier", 1)
            self.assertContains(search_response, document2.identifier, 1)

    @freeze_time("2024-09-24T12:00:00-00:00")
    def test_document_admin_create(self):
        publication = PublicationFactory.create()
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
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
            "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur."
        )

        add_response = form.submit(name="_save")

        self.assertRedirects(
            add_response, reverse("admin:publications_document_changelist")
        )
        added_item = Document.objects.order_by("-pk").first()
        assert added_item is not None
        self.assertEqual(added_item.publicatie, publication)
        self.assertEqual(added_item.identifier, identifier)
        self.assertEqual(
            added_item.officiele_titel, "The official title of this document"
        )
        self.assertEqual(added_item.verkorte_titel, "The title")
        self.assertEqual(
            added_item.omschrijving,
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris risus nibh, "
            "iaculis eu cursus sit amet, accumsan ac urna. Mauris interdum eleifend eros sed consectetur.",
        )
        self.assertEqual(str(added_item.registratiedatum), "2024-09-24 12:00:00+00:00")
        self.assertEqual(
            str(added_item.laatst_geweizigd_datum), "2024-09-24 12:00:00+00:00"
        )

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
        form["publicatie"] = publication.id
        form["identifier"] = identifier
        form["officiele_titel"] = "changed official title"
        form["verkorte_titel"] = "changed short title"
        form["omschrijving"] = "changed description"

        with freeze_time("2024-09-29T14:00:00-00:00"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)

        document.refresh_from_db()
        self.assertEqual(document.publicatie, publication)
        self.assertEqual(document.identifier, identifier)
        self.assertEqual(document.officiele_titel, "changed official title")
        self.assertEqual(document.verkorte_titel, "changed short title")
        self.assertEqual(document.omschrijving, "changed description")
        self.assertEqual(str(document.registratiedatum), "2024-09-25 14:00:00+00:00")
        self.assertEqual(
            str(document.laatst_geweizigd_datum), "2024-09-29 14:00:00+00:00"
        )

    def test_document_admin_delete(self):
        document = DocumentFactory.create(
            officiele_titel="title one",
            verkorte_titel="one",
            omschrijving="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
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
        self.assertFalse(
            Document.objects.filter(identifier=document.identifier).exists()
        )

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

        # test that default and document service are selectable but the zaak service isn't
        service_option_values = [option[0] for option in document_select.options]
        self.assertEqual(service_option_values, ["", str(service.pk)])
