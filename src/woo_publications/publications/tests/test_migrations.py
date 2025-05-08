from datetime import date

from django_test_migrations.contrib.unittest_case import MigratorTestCase

from woo_publications.logging.constants import Events


class TestDocumentOwnerMigration(MigratorTestCase):
    migrate_from = ("publications", "0020_topic_afbeelding")
    migrate_to = ("publications", "0021_document_eigenaar_publication_eigenaar")

    def prepare(self):
        """Prepare some data before the migration."""
        InformationCategory = self.old_state.apps.get_model(
            "metadata", "informationcategory"
        )
        Organisation = self.old_state.apps.get_model("metadata", "organisation")
        Publication = self.old_state.apps.get_model("publications", "publication")
        Document = self.old_state.apps.get_model("publications", "document")
        TimelineLogProxy = self.old_state.apps.get_model("logging", "timelinelogproxy")
        ContentType = self.old_state.apps.get_model("contenttypes", "contenttype")

        ic = InformationCategory.objects.create(
            order=1, naam="test", bron_bewaartermijn="Selectielijst gemeenten 2020"
        )
        org = Organisation.objects.create(naam="test", is_actief=True)
        pub_ct, _ = ContentType.objects.get_or_create(
            app_label="publications", model="publication"
        )
        doc_ct, _ = ContentType.objects.get_or_create(
            app_label="publications", model="document"
        )

        pub1 = Publication.objects.create(
            publisher=org,
            officiele_titel="first pub",
        )
        pub1.informatie_categorieen.set([ic])
        pub1.save()

        TimelineLogProxy.objects.create(
            content_type=pub_ct,
            object_id=pub1.pk,
            extra_data={
                "event": Events.create,
                "acting_user": {
                    "identifier": "identifier-1",
                    "display_name": "Brendan Murphy",
                },
            },
            user=None,
        )

        pub2 = Publication.objects.create(
            publisher=org,
            officiele_titel="second pub",
        )
        pub2.informatie_categorieen.set([ic])
        pub2.save()

        TimelineLogProxy.objects.create(
            content_type=pub_ct,
            object_id=pub2.pk,
            extra_data={
                "event": Events.create,
                "acting_user": {
                    "identifier": "identifier-2",
                    "display_name": "Phil Bozeman",
                },
            },
            user=None,
        )

        pub3 = Publication.objects.create(
            publisher=org,
            officiele_titel="third pub",
        )
        pub3.informatie_categorieen.set([ic])
        pub3.save()

        TimelineLogProxy.objects.create(
            content_type=pub_ct,
            object_id=pub3.pk,
            extra_data={
                "event": Events.create,
                "acting_user": {
                    "identifier": "identifier-3",
                    "display_name": "Vincent Bennett",
                },
            },
            user=None,
        )

        doc1 = Document.objects.create(
            publicatie=pub1, officiele_titel="first doc", creatiedatum=date(2025, 1, 1)
        )

        TimelineLogProxy.objects.create(
            content_type=doc_ct,
            object_id=doc1.pk,
            extra_data={
                "event": Events.create,
                "acting_user": {
                    "identifier": "identifier-3",
                    "display_name": "Vincent Bennett",
                },
            },
            user=None,
        )

    def test_migration_0021_document_eigenaar_publication_eigenaar(self):
        Publication = self.new_state.apps.get_model("publications", "publication")
        Document = self.new_state.apps.get_model("publications", "document")
        OrganisationMember = self.new_state.apps.get_model(
            "accounts", "organisationmember"
        )

        self.assertEqual(OrganisationMember.objects.count(), 3)

        pub1 = Publication.objects.get(officiele_titel="first pub")
        self.assertEqual(pub1.eigenaar.identifier, "identifier-1")
        self.assertEqual(pub1.eigenaar.naam, "Brendan Murphy")

        pub2 = Publication.objects.get(officiele_titel="second pub")
        self.assertEqual(pub2.eigenaar.identifier, "identifier-2")
        self.assertEqual(pub2.eigenaar.naam, "Phil Bozeman")

        pub3 = Publication.objects.get(officiele_titel="third pub")
        self.assertEqual(pub3.eigenaar.identifier, "identifier-3")
        self.assertEqual(pub3.eigenaar.naam, "Vincent Bennett")

        doc1 = Document.objects.get(officiele_titel="first doc")
        self.assertEqual(doc1.eigenaar.identifier, "identifier-3")
        self.assertEqual(doc1.eigenaar.naam, "Vincent Bennett")
