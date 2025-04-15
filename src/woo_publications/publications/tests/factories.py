from pathlib import Path
from typing import Sequence

from django.conf import settings

import factory

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.metadata.models import InformationCategory
from woo_publications.metadata.tests.factories import OrganisationFactory

from ..models import Document, Publication, Topic

TEST_IMG_PATH = (
    Path(settings.DJANGO_PROJECT_DIR)
    / "publications"
    / "tests"
    / "files"
    / "maykin_media_logo.jpeg"
)


class PublicationFactory(factory.django.DjangoModelFactory[Publication]):
    publisher = factory.SubFactory(OrganisationFactory, is_actief=True)
    officiele_titel = factory.Faker("word")

    class Meta:  # pyright: ignore
        model = Publication

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


class DocumentFactory(factory.django.DjangoModelFactory[Document]):
    publicatie = factory.SubFactory(PublicationFactory)
    officiele_titel = factory.Faker("word")
    creatiedatum = factory.Faker("past_date")

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
            document_uuid=factory.Faker("uuid4"),
        )


class TopicFactory(factory.django.DjangoModelFactory[Topic]):
    afbeelding = factory.django.ImageField(width=250, height=250, image_format="jpg")
    officiele_titel = factory.Faker("word")

    class Meta:  # pyright: ignore
        model = Topic
