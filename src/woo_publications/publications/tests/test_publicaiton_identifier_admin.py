from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from woo_publications.accounts.tests.factories import UserFactory
from woo_publications.metadata.tests.factories import InformationCategoryFactory
from woo_publications.publications.models import PublicationIdentifier
from woo_publications.publications.tests.factories import (
    PublicationFactory,
    PublicationIdentifierFactory,
)
from woo_publications.utils.tests.webtest import add_dynamic_field


@disable_admin_mfa()
class TestPublicationIdentifierAdmin(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_publicationidentifier_admin_shows_items(self):
        PublicationIdentifierFactory.create(
            kenmerk="openzaak",
            bron="documents api",
        )
        PublicationIdentifierFactory.create(
            kenmerk="gpp-zoeken",
            bron="search api",
        )
        response = self.app.get(
            reverse("admin:publications_publicationidentifier_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-bron", 2)

    def test_publicationidentifier_admin_search(self):
        publicatie, publicatie_2 = PublicationFactory.create_batch(2)
        PublicationIdentifierFactory.create(
            publicatie=publicatie,
            kenmerk="openzaak",
            bron="documents api",
        )
        PublicationIdentifierFactory.create(
            publicatie=publicatie_2,
            kenmerk="gpp-zoeken",
            bron="search api",
        )
        response = self.app.get(
            reverse("admin:publications_publicationidentifier_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms["changelist-search"]

        with self.subTest("search on kenmerk"):
            form["q"] = "gpp-zoeken"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-bron", 1)
            self.assertContains(
                search_response,
                "search api",
                1,
                html=True,
            )

        with self.subTest("search on bron"):
            form["q"] = "documents api"
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-kenmerk", 1)
            self.assertContains(search_response, "openzaak", 1, html=True)

        with self.subTest("search on publicatie"):
            form["q"] = str(publicatie.uuid)
            search_response = form.submit()

            self.assertEqual(search_response.status_code, 200)
            self.assertContains(search_response, "field-kenmerk", 1)
            self.assertContains(search_response, "openzaak", 1, html=True)

    def test_publicationidentifier_admin_create(self):
        publicatie = PublicationFactory.create()

        response = self.app.get(
            reverse("admin:publications_publicationidentifier_add"),
            user=self.user,
        )

        form = response.forms["publicationidentifier_form"]
        form["publicatie"].select(text=str(publicatie))
        form["kenmerk"] = "openzaak"
        form["bron"] = "documents api"

        create_response = form.submit("_save")

        self.assertEqual(create_response.status_code, 302)

        added_item = PublicationIdentifier.objects.get()

        self.assertEqual(added_item.publicatie, publicatie)
        self.assertEqual(added_item.kenmerk, "openzaak")
        self.assertEqual(added_item.bron, "documents api")

    def test_publicationidentifier_admin_update(self):
        publicatie, publicatie_2 = PublicationFactory.create_batch(2)

        publication_identifier = PublicationIdentifierFactory.create(
            publicatie=publicatie,
            kenmerk="openzaak",
            bron="documents api",
        )

        response = self.app.get(
            reverse(
                "admin:publications_publicationidentifier_change",
                kwargs={"object_id": publication_identifier.pk},
            ),
            user=self.user,
        )

        form = response.forms["publicationidentifier_form"]
        form["publicatie"].select(text=str(publicatie_2))
        form["kenmerk"] = "gpp-zoeken"
        form["bron"] = "search api"

        update_response = form.submit("_save")

        self.assertEqual(update_response.status_code, 302)

        publication_identifier.refresh_from_db()

        self.assertEqual(publication_identifier.publicatie, publicatie_2)
        self.assertEqual(publication_identifier.kenmerk, "gpp-zoeken")
        self.assertEqual(publication_identifier.bron, "search api")

    def test_publicationidentifier_admin_delete(self):
        publication_identifier = PublicationIdentifierFactory.create(
            kenmerk="openzaak",
            bron="documents api",
        )

        response = self.app.get(
            reverse(
                "admin:publications_publicationidentifier_delete",
                kwargs={"object_id": publication_identifier.pk},
            ),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)

        form = response.forms[1]

        with self.captureOnCommitCallbacks(execute=True):
            response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            PublicationIdentifier.objects.filter(pk=publication_identifier.pk).exists()
        )


@disable_admin_mfa()
class TestInlineInformationCategoryForPublicationAdmin(WebTest):
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
        add_dynamic_field(form, "publicationidentifier_set-0-kenmerk", "openzaak")
        add_dynamic_field(
            form,
            "publicationidentifier_set-0-bron",
            "documents api",
        )

        create_response = form.submit(name="_save")

        self.assertEqual(create_response.status_code, 302)

        added_item = PublicationIdentifier.objects.get()

        self.assertEqual(added_item.publicatie, publication)
        self.assertEqual(added_item.kenmerk, "openzaak")
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
        add_dynamic_field(form, "publicationidentifier_set-0-kenmerk", "openzaak")
        add_dynamic_field(
            form,
            "publicationidentifier_set-0-bron",
            "documents api",
        )

        update_response = form.submit(name="_save")

        self.assertEqual(update_response.status_code, 302)

        publicationidentifier.refresh_from_db()

        self.assertEqual(publicationidentifier.publicatie, publication)
        self.assertEqual(publicationidentifier.kenmerk, "openzaak")
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
