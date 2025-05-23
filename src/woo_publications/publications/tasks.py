import logging
from typing import Literal, assert_never
from uuid import UUID

from woo_publications.celery import app
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.gpp_zoeken.client import get_client
from woo_publications.publications.constants import PublicationStatusOptions

from .models import Document, Publication, Topic

logger = logging.getLogger(__name__)


@app.task
def index_document(*, document_id: int, download_url: str = "") -> str | None:
    """
    Offer the document data to the gpp-zoeken service for indexing.

    If no service is configured or the document publication status is not suitable
    for public indexing, then the index operation is skipped.

    :returns: The remote task ID or None if the indexing was skipped.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info("No GPP search service configured, skipping the indexing task.")
        return

    document = Document.objects.select_related(
        "publicatie", "publicatie__publisher"
    ).get(pk=document_id)
    if (
        current_status := document.publicatiestatus
    ) != PublicationStatusOptions.published:
        logger.info("Document has publication status %s, skipping.", current_status)
        return

    if not document.upload_complete:
        logger.info(
            "Document upload is not yet complete, skipping.",
            extra={"document": document.uuid},
        )
        return

    if (
        not (pub_status := document.publicatie.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        logger.info(
            "Related publication of document has publication status %s, skipping.",
            pub_status,
        )
        return

    with get_client(service) as client:
        return client.index_document(document=document, download_url=download_url)


@app.task
def remove_document_from_index(*, document_id: int, force: bool = False) -> str | None:
    """
    Remove the document from the GPP-zoeken index, if the status requires it.

    If no service is configured or the document publication status is published, then
    the remove-from-index-operation is skipped.

    :returns: The remote task ID or None if the index removal was skipped.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info(
            "No GPP search service configured, skipping the index removal task."
        )
        return

    document = Document.objects.get(pk=document_id)
    if (
        (current_status := document.publicatiestatus)
        and not force
        and (
            current_status == PublicationStatusOptions.concept
            or current_status == PublicationStatusOptions.published
        )
    ):
        logger.info(
            "Document has publication status %s, skipping index removal.",
            current_status,
        )
        return

    with get_client(service) as client:
        return client.remove_document_from_index(document, force)


@app.task
def index_publication(*, publication_id: int) -> str | None:
    """
    Offer the publication data to the gpp-zoeken service for indexing.

    If no service is configured or the publication status is not suitable
    for public indexing, then the index operation is skipped.

    :returns: The remote task ID or None if the indexing was skipped.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info("No GPP search service configured, skipping the indexing task.")
        return

    publication = Publication.objects.get(pk=publication_id)
    if (
        current_status := publication.publicatiestatus
    ) != PublicationStatusOptions.published:
        logger.info("Publication has publication status %s, skipping.", current_status)
        return

    with get_client(service) as client:
        return client.index_publication(publication)


@app.task
def remove_publication_from_index(
    *, publication_id: int, force: bool = False
) -> str | None:
    """
    Remove the publication from the GPP-zoeken index, if the status requires it.

    If no service is configured or the publication status is published, then
    the remove-from-index-operation is skipped.

    :returns: The remote task ID or None if the index removal was skipped.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info(
            "No GPP search service configured, skipping the index removal task."
        )
        return

    publication = Publication.objects.get(pk=publication_id)
    if (
        not force
        and (current_status := publication.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        logger.info(
            "publication has publication status %s, skipping index removal.",
            current_status,
        )
        return

    with get_client(service) as client:
        return client.remove_publication_from_index(publication, force)


@app.task
def index_topic(*, topic_id: int) -> str | None:
    """
    Offer the topic data to the gpp-zoeken service for indexing.

    If no service is configured or the topic publication status is not suitable
    for public indexing, then the index operation is skipped.

    :returns: The remote task ID or None if the indexing was skipped.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info("No GPP search service configured, skipping the indexing task.")
        return

    topic = Topic.objects.get(pk=topic_id)
    if (current_status := topic.publicatiestatus) != PublicationStatusOptions.published:
        logger.info("Topic has publication status %s, skipping.", current_status)
        return

    with get_client(service) as client:
        return client.index_topic(topic=topic)


@app.task
def remove_topic_from_index(*, topic_id: int, force: bool = False) -> str | None:
    """
    Remove the topic from the GPP-zoeken index, if the status requires it.

    If no service is configured or the topic status is published, then
    the remove-from-index-operation is skipped.

    :returns: The remote task ID or None if the index removal was skipped.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info(
            "No GPP search service configured, skipping the index removal task."
        )
        return

    topic = Topic.objects.get(pk=topic_id)
    if (
        not force
        and (current_status := topic.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        logger.info(
            "topic has publication status %s, skipping index removal.",
            current_status,
        )
        return

    with get_client(service) as client:
        return client.remove_topic_from_index(topic, force)


@app.task
def remove_from_index_by_uuid(
    *,
    model_name: Literal["Document", "Publication", "Topic"],
    uuid: str | UUID,
    force: bool = False,
) -> str | None:
    """
    Force removal from the index for records that are deleted from the database.

    We must create instances on the fly because the DB records have been deleted on
    successful database transaction commit.
    """
    config = GlobalConfiguration.get_solo()
    if (service := config.gpp_search_service) is None:
        logger.info(
            "No GPP search service configured, skipping the index removal task."
        )
        return

    with get_client(service) as client:
        match model_name:
            case "Document":
                document = Document(
                    uuid=uuid, publicatiestatus=PublicationStatusOptions.revoked
                )
                return client.remove_document_from_index(document, force)
            case "Publication":
                publication = Publication(
                    uuid=uuid, publicatiestatus=PublicationStatusOptions.revoked
                )
                return client.remove_publication_from_index(publication, force)
            case "Topic":
                topic = Topic(
                    uuid=uuid, publicatiestatus=PublicationStatusOptions.revoked
                )
                return client.remove_topic_from_index(topic, force)
            case _:  # pragma: no cover
                assert_never(model_name)
