import logging
from typing import Literal
from uuid import UUID

from woo_publications.celery import app
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.gpp_zoeken.client import get_client
from woo_publications.publications.constants import PublicationStatusOptions

from .models import Document, Publication

logger = logging.getLogger(__name__)


@app.task
def index_document(*, document_id: int) -> str | None:
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
        return client.index_document(document)


@app.task
def remove_document_from_index(*, document_id: int) -> str | None:
    """
    Remove the document from the GPP Zoeken index, if the status requires it.

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
        current_status := document.publicatiestatus
    ) == PublicationStatusOptions.published:
        logger.info(
            "Document has publication status %s, skipping index removal.",
            current_status,
        )
        return

    with get_client(service) as client:
        return client.remove_document_from_index(document)


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
def remove_publication_from_index(*, publication_id: int) -> str | None:
    """
    Remove the publication from the GPP Zoeken index, if the status requires it.

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
        current_status := publication.publicatiestatus
    ) == PublicationStatusOptions.published:
        logger.info(
            "publication has publication status %s, skipping index removal.",
            current_status,
        )
        return

    with get_client(service) as client:
        return client.remove_publication_from_index(publication)


@app.task
def remove_from_index_by_uuid(
    *,
    model_name: Literal["Document", "Publication"],
    uuid: str | UUID,
) -> str | None:
    """
    Force removal from the index for records that are deleted from the databse.

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
                return client.remove_document_from_index(document)
            case "Publication":
                publication = Publication(
                    uuid=uuid, publicatiestatus=PublicationStatusOptions.revoked
                )
                return client.remove_publication_from_index(publication)
