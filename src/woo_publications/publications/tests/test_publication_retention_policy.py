from datetime import date

from django.urls import reverse

from django_webtest import WebTest
from freezegun import freeze_time
from maykin_2fa.test import disable_admin_mfa
from rest_framework import status
from rest_framework.test import APITestCase

from woo_publications.accounts.tests.factories import (
    OrganisationMemberFactory,
    UserFactory,
)
from woo_publications.api.tests.mixins import APITestCaseMixin, TokenAuthMixin
from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.tests.factories import (
    InformationCategoryFactory,
    OrganisationFactory,
)

from ..constants import PublicationStatusOptions
from ..models import Publication
from .factories import PublicationFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


@disable_admin_mfa()
class TestPublicationsAdminRetentionPolicy(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_create_concept_publication_retention_policy_not_applied(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
        form["publisher"] = str(organisation.pk)
        form["officiele_titel"] = "The official title of this publication"
        form["bron_bewaartermijn"] = "NOT REPLACED"
        form["selectiecategorie"] = "NOT REPLACED"
        form["archiefnominatie"].select(text=ArchiveNominationChoices.destroy.label)
        form["archiefactiedatum"] = "2000-01-01"
        form["toelichting_bewaartermijn"] = "NOT REPLACED"

        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        added_item = Publication.objects.get()
        self.assertEqual(added_item.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(added_item.selectiecategorie, "NOT REPLACED")
        self.assertEqual(added_item.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(str(added_item.archiefactiedatum), "2000-01-01")
        self.assertEqual(added_item.toelichting_bewaartermijn, "NOT REPLACED")

    def test_create_published_publication_retention_policy_applied(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        reverse_url = reverse("admin:publications_publication_add")

        response = self.app.get(reverse_url, user=self.user)

        self.assertEqual(response.status_code, 200)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["publisher"] = str(organisation.pk)
        form["officiele_titel"] = "The official title of this publication"
        form["bron_bewaartermijn"] = "NOT REPLACED"
        form["selectiecategorie"] = "NOT REPLACED"
        form["archiefnominatie"].select(text=ArchiveNominationChoices.destroy.label)
        form["archiefactiedatum"] = "2000-01-01"
        form["toelichting_bewaartermijn"] = "NOT REPLACED"

        with freeze_time("2025-01-01"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        added_item = Publication.objects.get()
        self.assertEqual(added_item.bron_bewaartermijn, "bewaartermijn")
        self.assertEqual(added_item.selectiecategorie, "selectiecategorie")
        self.assertEqual(added_item.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(str(added_item.archiefactiedatum), "2030-01-01")
        self.assertEqual(added_item.toelichting_bewaartermijn, "toelichting")

    def test_update_concept_publication_retention_policy_not_applied(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            eigenaar=self.organisation_member,
            publisher=organisation,
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.concept,
            officiele_titel="title one",
            bron_bewaartermijn="NOT REPLACED",
            selectiecategorie="NOT REPLACED",
            archiefnominatie=ArchiveNominationChoices.destroy,
            archiefactiedatum=date(2000, 1, 1),
            toelichting_bewaartermijn="NOT REPLACED",
        )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id, ic2.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.concept.label)
        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(publication.selectiecategorie, "NOT REPLACED")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(str(publication.archiefactiedatum), "2000-01-01")
        self.assertEqual(publication.toelichting_bewaartermijn, "NOT REPLACED")

    def test_update_to_publish_retention_policy_applied(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2025-01-01"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                informatie_categorieen=[ic],
                publicatiestatus=PublicationStatusOptions.concept,
                officiele_titel="title one",
                bron_bewaartermijn="NOT REPLACED",
                selectiecategorie="NOT REPLACED",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum=date(2000, 1, 1),
                toelichting_bewaartermijn="NOT REPLACED",
            )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )
        response = self.app.get(reverse_url, user=self.user)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id, ic2.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)

        with freeze_time("2025-01-10"):
            response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn")
        self.assertEqual(publication.selectiecategorie, "selectiecategorie")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(str(publication.archiefactiedatum), "2030-01-10")
        self.assertEqual(publication.toelichting_bewaartermijn, "toelichting")

    def test_update_published_publication_retention_policy_not_applied(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            eigenaar=self.organisation_member,
            publisher=organisation,
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.published,
            officiele_titel="title one",
            bron_bewaartermijn="NOT REPLACED",
            selectiecategorie="NOT REPLACED",
            archiefnominatie=ArchiveNominationChoices.destroy,
            archiefactiedatum=date(2000, 1, 1),
            toelichting_bewaartermijn="NOT REPLACED",
        )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        form = response.forms["publication_form"]
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        form["officiele_titel"] = "bla"
        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(publication.selectiecategorie, "NOT REPLACED")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(str(publication.archiefactiedatum), "2000-01-01")
        self.assertEqual(publication.toelichting_bewaartermijn, "NOT REPLACED")

    def test_update_published_publication_with_new_ic_retention_policy_applied(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2025-01-01"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                informatie_categorieen=[ic],
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                bron_bewaartermijn="NOT REPLACED",
                selectiecategorie="NOT REPLACED",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum=date(2000, 1, 1),
                toelichting_bewaartermijn="NOT REPLACED",
            )

        reverse_url = reverse(
            "admin:publications_publication_change",
            kwargs={"object_id": publication.id},
        )

        response = self.app.get(reverse_url, user=self.user)

        form = response.forms["publication_form"]
        form["informatie_categorieen"].force_value([ic.id, ic2.id])
        form["publicatiestatus"].select(text=PublicationStatusOptions.published.label)
        response = form.submit(name="_save")

        self.assertEqual(response.status_code, 302)
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn")
        self.assertEqual(publication.selectiecategorie, "selectiecategorie")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(str(publication.archiefactiedatum), "2030-01-01")
        self.assertEqual(publication.toelichting_bewaartermijn, "toelichting")

    def test_bulk_retention_field_update_action(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="Selectielijst gemeenten 2020",
            selectiecategorie="20.1.2",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=10,
            toelichting_bewaartermijn="extra data",
        )
        with freeze_time("2025-01-01T00:00:00-00:00"):
            concept = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.concept,
                informatie_categorieen=[ic],
                bron_bewaartermijn="NOT REPLACED",
                selectiecategorie="NOT REPLACED",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum="2030-01-01",
                toelichting_bewaartermijn="NOT REPLACED",
            )
            published = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                informatie_categorieen=[ic],
                bron_bewaartermijn="SOON TO BE UPDATED LIST OF 2020",
                selectiecategorie="2",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum="2025-01-01",
                toelichting_bewaartermijn="bla bla bla",
            )
            revoked = PublicationFactory.create(
                publicatiestatus=PublicationStatusOptions.published,
                informatie_categorieen=[ic],
                bron_bewaartermijn="SOON TO BE UPDATED LIST OF 2014",
                selectiecategorie="1",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum="2020-01-01",
                toelichting_bewaartermijn="bla bla bla",
            )
            # have to manually update this because of the model save assertion
            revoked.publicatiestatus = PublicationStatusOptions.revoked
            revoked.save()

        changelist = self.app.get(
            reverse("admin:publications_publication_changelist"),
            user=self.user,
        )
        form = changelist.forms["changelist-form"]

        form["_selected_action"] = [pub.pk for pub in Publication.objects.all()]
        form["action"] = "reassess_retention_policy"
        form.submit()

        concept.refresh_from_db()
        published.refresh_from_db()
        revoked.refresh_from_db()

        # concept not updated
        self.assertEqual(concept.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(concept.selectiecategorie, "NOT REPLACED")
        self.assertEqual(concept.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(concept.archiefactiedatum, date(2030, 1, 1))
        self.assertEqual(concept.toelichting_bewaartermijn, "NOT REPLACED")

        # published and revoked updated
        for pub in [published, revoked]:
            self.assertEqual(pub.bron_bewaartermijn, "Selectielijst gemeenten 2020")
            self.assertEqual(pub.selectiecategorie, "20.1.2")
            self.assertEqual(pub.archiefnominatie, ArchiveNominationChoices.retain)
            self.assertEqual(pub.archiefactiedatum, date(2035, 1, 1))
            self.assertEqual(pub.toelichting_bewaartermijn, "extra data")


class TestPublicationsApiRetentionPolicy(TokenAuthMixin, APITestCaseMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)
        cls.organisation_member = OrganisationMemberFactory.create(
            identifier=cls.user.pk,
            naam=cls.user.get_full_name(),
        )

    def test_create_concept_publication_retention_policy_not_applied(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        url = reverse("api:publication-list")

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publicatiestatus": PublicationStatusOptions.concept,
            "publisher": str(organisation.uuid),
            "officieleTitel": "title one",
            "bronBewaartermijn": "NOT REPLACED",
            "selectiecategorie": "NOT REPLACED",
            "archiefnominatie": ArchiveNominationChoices.destroy,
            "archiefactiedatum": "2000-01-01",
            "toelichtingBewaartermijn": "NOT REPLACED",
        }

        response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data["bronBewaartermijn"], "NOT REPLACED")
        self.assertEqual(response_data["selectiecategorie"], "NOT REPLACED")
        self.assertEqual(
            response_data["archiefnominatie"], ArchiveNominationChoices.destroy
        )
        self.assertEqual(response_data["archiefactiedatum"], "2000-01-01")
        self.assertEqual(response_data["toelichtingBewaartermijn"], "NOT REPLACED")
        publication = Publication.objects.get()
        self.assertEqual(publication.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(publication.selectiecategorie, "NOT REPLACED")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(publication.archiefactiedatum, date(2000, 1, 1))
        self.assertEqual(publication.toelichting_bewaartermijn, "NOT REPLACED")

    def test_create_published_publication_retention_policy_applied(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        url = reverse("api:publication-list")

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publicatiestatus": PublicationStatusOptions.published,
            "publisher": str(organisation.uuid),
            "officieleTitel": "title one",
            "bronBewaartermijn": "NOT REPLACED",
            "selectiecategorie": "NOT REPLACED",
            "archiefnominatie": ArchiveNominationChoices.destroy,
            "archiefactiedatum": "2000-01-01",
            "toelichtingBewaartermijn": "NOT REPLACED",
        }

        with freeze_time("2025-01-01"):
            response = self.client.post(url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertEqual(response_data["bronBewaartermijn"], "bewaartermijn")
        self.assertEqual(response_data["selectiecategorie"], "selectiecategorie")
        self.assertEqual(
            response_data["archiefnominatie"], ArchiveNominationChoices.retain
        )
        self.assertEqual(response_data["archiefactiedatum"], "2030-01-01")
        self.assertEqual(response_data["toelichtingBewaartermijn"], "toelichting")
        publication = Publication.objects.get()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn")
        self.assertEqual(publication.selectiecategorie, "selectiecategorie")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(publication.archiefactiedatum, date(2030, 1, 1))
        self.assertEqual(publication.toelichting_bewaartermijn, "toelichting")

    def test_update_concept_publication_retention_policy_not_applied(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        publication = PublicationFactory.create(
            eigenaar=self.organisation_member,
            publisher=organisation,
            informatie_categorieen=[ic],
            publicatiestatus=PublicationStatusOptions.concept,
            officiele_titel="title one",
            bron_bewaartermijn="NOT REPLACED",
            selectiecategorie="NOT REPLACED",
            archiefnominatie=ArchiveNominationChoices.destroy,
            archiefactiedatum=date(2000, 1, 1),
            toelichting_bewaartermijn="NOT REPLACED",
        )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "informatieCategorieen": [str(ic.uuid), str(ic2.uuid)],
            "publicatiestatus": PublicationStatusOptions.concept,
            "publisher": str(organisation.uuid),
            "officieleTitel": "title one",
            "bronBewaartermijn": "NOT REPLACED",
            "selectiecategorie": "NOT REPLACED",
            "archiefnominatie": ArchiveNominationChoices.destroy,
            "archiefactiedatum": "2000-01-01",
            "toelichtingBewaartermijn": "NOT REPLACED",
        }

        response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["bronBewaartermijn"], "NOT REPLACED")
        self.assertEqual(response_data["selectiecategorie"], "NOT REPLACED")
        self.assertEqual(
            response_data["archiefnominatie"], ArchiveNominationChoices.destroy
        )
        self.assertEqual(response_data["archiefactiedatum"], "2000-01-01")
        self.assertEqual(response_data["toelichtingBewaartermijn"], "NOT REPLACED")
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(publication.selectiecategorie, "NOT REPLACED")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(publication.archiefactiedatum, date(2000, 1, 1))
        self.assertEqual(publication.toelichting_bewaartermijn, "NOT REPLACED")

    def test_update_to_publish_retention_policy_applied(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2025-01-01"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                informatie_categorieen=[ic],
                publicatiestatus=PublicationStatusOptions.concept,
                officiele_titel="title one",
                bron_bewaartermijn="NOT REPLACED",
                selectiecategorie="NOT REPLACED",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum=date(2000, 1, 1),
                toelichting_bewaartermijn="NOT REPLACED",
            )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publicatiestatus": PublicationStatusOptions.published,
            "publisher": str(organisation.uuid),
            "officieleTitel": "title one",
            "bronBewaartermijn": "NOT REPLACED",
            "selectiecategorie": "NOT REPLACED",
            "archiefnominatie": ArchiveNominationChoices.destroy,
            "archiefactiedatum": "2000-01-01",
            "toelichtingBewaartermijn": "NOT REPLACED",
        }

        # use different time when the publication was published
        with freeze_time("2030-01-01"):
            response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["bronBewaartermijn"], "bewaartermijn")
        self.assertEqual(response_data["selectiecategorie"], "selectiecategorie")
        self.assertEqual(
            response_data["archiefnominatie"], ArchiveNominationChoices.retain
        )
        self.assertEqual(response_data["archiefactiedatum"], "2035-01-01")
        self.assertEqual(response_data["toelichtingBewaartermijn"], "toelichting")
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn")
        self.assertEqual(publication.selectiecategorie, "selectiecategorie")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(publication.archiefactiedatum, date(2035, 1, 1))
        self.assertEqual(publication.toelichting_bewaartermijn, "toelichting")

    def test_update_published_publication_retention_policy_not_applied(self):
        ic = InformationCategoryFactory.create(
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2025-01-01"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                informatie_categorieen=[ic],
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                bron_bewaartermijn="NOT REPLACED",
                selectiecategorie="NOT REPLACED",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum=date(2000, 1, 1),
                toelichting_bewaartermijn="NOT REPLACED",
            )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "informatieCategorieen": [str(ic.uuid)],
            "publicatiestatus": PublicationStatusOptions.published,
            "publisher": str(organisation.uuid),
            "officieleTitel": "title one",
            "bronBewaartermijn": "NOT REPLACED",
            "selectiecategorie": "NOT REPLACED",
            "archiefnominatie": ArchiveNominationChoices.destroy,
            "archiefactiedatum": "2000-01-01",
            "toelichtingBewaartermijn": "NOT REPLACED",
        }

        response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["bronBewaartermijn"], "NOT REPLACED")
        self.assertEqual(response_data["selectiecategorie"], "NOT REPLACED")
        self.assertEqual(
            response_data["archiefnominatie"], ArchiveNominationChoices.destroy
        )
        self.assertEqual(response_data["archiefactiedatum"], "2000-01-01")
        self.assertEqual(response_data["toelichtingBewaartermijn"], "NOT REPLACED")
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "NOT REPLACED")
        self.assertEqual(publication.selectiecategorie, "NOT REPLACED")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.destroy)
        self.assertEqual(publication.archiefactiedatum, date(2000, 1, 1))
        self.assertEqual(publication.toelichting_bewaartermijn, "NOT REPLACED")

    def test_update_published_publication_with_new_ic_retention_policy_applied(self):
        ic, ic2 = InformationCategoryFactory.create_batch(
            2,
            bron_bewaartermijn="bewaartermijn",
            selectiecategorie="selectiecategorie",
            archiefnominatie=ArchiveNominationChoices.retain,
            bewaartermijn=5,
            toelichting_bewaartermijn="toelichting",
        )
        organisation = OrganisationFactory.create(is_actief=True)
        with freeze_time("2025-01-01"):
            publication = PublicationFactory.create(
                eigenaar=self.organisation_member,
                publisher=organisation,
                informatie_categorieen=[ic],
                publicatiestatus=PublicationStatusOptions.published,
                officiele_titel="title one",
                bron_bewaartermijn="NOT REPLACED",
                selectiecategorie="NOT REPLACED",
                archiefnominatie=ArchiveNominationChoices.destroy,
                archiefactiedatum=date(2000, 1, 1),
                toelichting_bewaartermijn="NOT REPLACED",
            )
        detail_url = reverse(
            "api:publication-detail",
            kwargs={"uuid": str(publication.uuid)},
        )

        data = {
            "informatieCategorieen": [str(ic.uuid), str(ic2.uuid)],
            "publicatiestatus": PublicationStatusOptions.published,
            "publisher": str(organisation.uuid),
            "officieleTitel": "title one",
            "bronBewaartermijn": "NOT REPLACED",
            "selectiecategorie": "NOT REPLACED",
            "archiefnominatie": ArchiveNominationChoices.destroy,
            "archiefactiedatum": "2000-01-01",
            "toelichtingBewaartermijn": "NOT REPLACED",
        }

        response = self.client.put(detail_url, data, headers=AUDIT_HEADERS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["bronBewaartermijn"], "bewaartermijn")
        self.assertEqual(response_data["selectiecategorie"], "selectiecategorie")
        self.assertEqual(
            response_data["archiefnominatie"], ArchiveNominationChoices.retain
        )
        self.assertEqual(response_data["archiefactiedatum"], "2030-01-01")
        self.assertEqual(response_data["toelichtingBewaartermijn"], "toelichting")
        publication.refresh_from_db()
        self.assertEqual(publication.bron_bewaartermijn, "bewaartermijn")
        self.assertEqual(publication.selectiecategorie, "selectiecategorie")
        self.assertEqual(publication.archiefnominatie, ArchiveNominationChoices.retain)
        self.assertEqual(publication.archiefactiedatum, date(2030, 1, 1))
        self.assertEqual(publication.toelichting_bewaartermijn, "toelichting")
