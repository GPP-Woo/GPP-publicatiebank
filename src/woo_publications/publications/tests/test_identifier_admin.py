from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.publications.models import (
    DocumentIdentifier,
    PublicationIdentifier,
)
from woo_publications.publications.tests.factories import (
    DocumentFactory,
    DocumentIdentifierFactory,
    PublicationFactory,
    PublicationIdentifierFactory,
)
from woo_publications.utils.tests.webtest import add_dynamic_field


@disable_admin_mfa()
class TestInlinePublicationIdentifierForPublicationAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_inline_publicationidentifier_admin_create(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["publicationidentifier_set-TOTAL_FORMS"] = (
            "1"  # we're adding one, dynamically
        )
        add_dynamic_field(form, "publicationidentifier_set-0-kenmerk", "OZ-123")
        add_dynamic_field(
            form,
            "publicationidentifier_set-0-bron",
            "documents api",
        )

        create_response = form.submit(name="_save")

        self.assertEqual(create_response.status_code, 302)

        added_item = PublicationIdentifier.objects.get()

        self.assertEqual(added_item.publicatie, publication)
        self.assertEqual(added_item.kenmerk, "OZ-123")
        self.assertEqual(added_item.bron, "documents api")

    def test_inline_publicationidentifier_admin_update(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
        )
        publicationidentifier = PublicationIdentifierFactory.create(
            publicatie=publication,
            kenmerk="gpp-zoeken",
            bron="search api",
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        add_dynamic_field(form, "publicationidentifier_set-0-kenmerk", "OZ-123")
        add_dynamic_field(
            form,
            "publicationidentifier_set-0-bron",
            "documents api",
        )

        update_response = form.submit(name="_save")

        self.assertEqual(update_response.status_code, 302)

        publicationidentifier.refresh_from_db()

        self.assertEqual(publicationidentifier.publicatie, publication)
        self.assertEqual(publicationidentifier.kenmerk, "OZ-123")
        self.assertEqual(
            publicationidentifier.bron,
            "documents api",
        )

    def test_inline_publicationidentifier_admin_delete(self):
        ic = InformationCategoryFactory.create()
        publication = PublicationFactory.create(
            informatie_categorieen=[ic],
            officiele_titel="title one",
        )
        publicationidentifier = PublicationIdentifierFactory.create(
            publicatie=publication,
            kenmerk="gpp-zoeken",
            bron="search api",
        )
        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["publicationidentifier_set-0-DELETE"] = True

        delete_response = form.submit(name="_save")

        self.assertEqual(delete_response.status_code, 302)

        self.assertFalse(
            PublicationIdentifier.objects.filter(pk=publicationidentifier.id).exists()
        )


@disable_admin_mfa()
class TestInlineDocumentIdentifierForPublicationAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_inline_documentidentifier_admin_create(self):
        document = DocumentFactory.create(
            officiele_titel="title one",
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["documentidentifier_set-TOTAL_FORMS"] = (
            "1"  # we're adding one, dynamically
        )
        add_dynamic_field(form, "documentidentifier_set-0-kenmerk", "OZ-123")
        add_dynamic_field(
            form,
            "documentidentifier_set-0-bron",
            "documents api",
        )

        create_response = form.submit(name="_save")

        self.assertEqual(create_response.status_code, 302)

        added_item = DocumentIdentifier.objects.get()

        self.assertEqual(added_item.document, document)
        self.assertEqual(added_item.kenmerk, "OZ-123")
        self.assertEqual(added_item.bron, "documents api")

    def test_inline_documentidentifier_admin_update(self):
        document = DocumentFactory.create(
            officiele_titel="title one",
        )
        documentidentifier = DocumentIdentifierFactory.create(
            document=document,
            kenmerk="gpp-zoeken",
            bron="search api",
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        add_dynamic_field(form, "documentidentifier_set-0-kenmerk", "OZ-123")
        add_dynamic_field(
            form,
            "documentidentifier_set-0-bron",
            "documents api",
        )

        update_response = form.submit(name="_save")

        self.assertEqual(update_response.status_code, 302)

        documentidentifier.refresh_from_db()

        self.assertEqual(documentidentifier.document, document)
        self.assertEqual(documentidentifier.kenmerk, "OZ-123")
        self.assertEqual(
            documentidentifier.bron,
            "documents api",
        )

    def test_inline_documentidentifier_admin_delete(self):
        document = DocumentFactory.create(
            officiele_titel="title one",
        )
        documentidentifier = DocumentIdentifierFactory.create(
            document=document,
            kenmerk="gpp-zoeken",
            bron="search api",
        )
        reverse_url = reverse(
            "admin:publications_document_change",
            kwargs={"object_id": document.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["document_form"]
        form["documentidentifier_set-0-DELETE"] = True

        delete_response = form.submit(name="_save")

        self.assertEqual(delete_response.status_code, 302)

        self.assertFalse(
            DocumentIdentifier.objects.filter(pk=documentidentifier.id).exists()
        )
