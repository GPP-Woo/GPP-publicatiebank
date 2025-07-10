from collections.abc import Sequence
from pathlib import Path

from django.conf import settings

import factory

from woo_publications.accounts.tests.factories import OrganisationMemberFactory
from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.models import InformationCategory
from woo_publications.metadata.tests.factories import OrganisationFactory

from ..constants import PublicationStatusOptions
from ..models import (
    Document,
    DocumentIdentifier,
    Publication,
    PublicationIdentifier,
    Topic,
)

TEST_IMG_PATH = (
    Path(settings.DJANGO_PROJECT_DIR)
    / "publications"
    / "tests"
    / "files"
    / "maykin_media_logo.jpeg"
)


class PublicationFactory(factory.django.DjangoModelFactory[Publication]):
    publisher = factory.SubFactory(OrganisationFactory, is_actief=True)
    eigenaar = factory.SubFactory(OrganisationMemberFactory)
    officiele_titel = factory.Faker("word")
    publicatiestatus = PublicationStatusOptions.published

    class Meta:  # pyright: ignore
        model = Publication

    class Params:
        revoked = factory.Trait(
            _revoke=factory.PostGenerationMethodCall(
                "revoke",
                user={"identifier": "factory_boy", "display_name": "Test factory"},
            )
        )

    @factory.post_generation
    def publicatiestatus_dates(
        obj: Publication,  # pyright: ignore[reportGeneralTypeIssues]
        create: bool,
        extracted: Sequence[InformationCategory],
        **kwargs,
    ):
        if not create:
            return

        if obj.publicatiestatus == PublicationStatusOptions.published:
            obj.gepubliceerd_op = obj.registratiedatum

    @factory.post_generation
    def informatie_categorieen(
        obj: Publication,  # pyright: ignore[reportGeneralTypeIssues]
        create: bool,
        extracted: Sequence[InformationCategory],
        **kwargs,
    ):
        if not create:
            return

        if extracted:
            obj.informatie_categorieen.set(extracted)

    @factory.post_generation
    def onderwerpen(
        obj: Publication,  # pyright: ignore[reportGeneralTypeIssues]
        create: bool,
        extracted: Sequence[Topic],
        **kwargs,
    ):
        if not create:
            return

        if extracted:
            obj.onderwerpen.set(extracted)


class PublicationIdentifierFactory(
    factory.django.DjangoModelFactory[PublicationIdentifier]
):
    publicatie = factory.SubFactory(PublicationFactory)
    kenmerk = factory.Sequence(lambda n: f"kenmerk-{n}")
    bron = factory.Sequence(lambda n: f"bron-{n}")

    class Meta:  # pyright: ignore
        model = PublicationIdentifier


class DocumentFactory(factory.django.DjangoModelFactory[Document]):
    publicatie = factory.SubFactory(PublicationFactory)
    eigenaar = factory.SubFactory(OrganisationMemberFactory)
    officiele_titel = factory.Faker("word")
    creatiedatum = factory.Faker("past_date")
    publicatiestatus = PublicationStatusOptions.published

    class Meta:  # pyright: ignore
        model = Document

    class Params:
        with_registered_document = factory.Trait(
            # Configured against the Open Zaak in our docker-compose.yml.
            # See the fixtures in docker/open-zaak.
            document_service=factory.SubFactory(
                ServiceFactory,
                for_documents_api_docker_compose=True,
            ),
            document_uuid=factory.Faker("uuid4", cast_to=None),
        )

    @factory.post_generation
    def _validate_publication_state(obj, *args, **kwargs):
        """
        Ensure that the factories are in a consistent state.
        """
        try:
            publication = obj.publicatie
        except Publication.DoesNotExist as exc:
            raise ValueError("A document must be related to a publication.") from exc

        assert isinstance(publication, Publication)

        match publication.publicatiestatus:
            case PublicationStatusOptions.concept:
                if not obj.publicatiestatus == PublicationStatusOptions.concept:
                    raise ValueError(
                        "'concept' publications can only have 'concept' documents."
                    )
            case PublicationStatusOptions.published:
                if obj.publicatiestatus not in (
                    PublicationStatusOptions.published,
                    PublicationStatusOptions.revoked,
                ):
                    raise ValueError(
                        "'published' publications can only have 'published' and "
                        "'revoked' documents."
                    )

            case PublicationStatusOptions.revoked:
                if not obj.publicatiestatus == PublicationStatusOptions.revoked:
                    raise ValueError(
                        "'revoked' publications can only have 'revoked' documents."
                    )

    @factory.post_generation
    def publicatiestatus_dates(
        obj: Document,  # pyright: ignore[reportGeneralTypeIssues]
        create: bool,
        extracted: Sequence[InformationCategory],
        **kwargs,
    ):
        if not create:
            return

        if obj.publicatiestatus == PublicationStatusOptions.published:
            obj.gepubliceerd_op = obj.registratiedatum


class DocumentIdentifierFactory(factory.django.DjangoModelFactory[DocumentIdentifier]):
    document = factory.SubFactory(DocumentFactory)
    kenmerk = factory.Sequence(lambda n: f"kenmerk-{n}")
    bron = factory.Sequence(lambda n: f"bron-{n}")

    class Meta:  # pyright: ignore
        model = DocumentIdentifier


class TopicFactory(factory.django.DjangoModelFactory[Topic]):
    afbeelding = factory.django.ImageField(width=10, height=10, image_format="jpg")
    officiele_titel = factory.Faker("word")

    class Meta:  # pyright: ignore
        model = Topic
