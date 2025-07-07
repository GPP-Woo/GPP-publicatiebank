import logging
from typing import Literal, assert_never
from urllib.parse import urljoin
from uuid import UUID

from zgw_consumers.models import Service

from woo_publications.celery import app
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import (
    PartsDownloader,
    get_client as get_documents_client,
)
from woo_publications.contrib.gpp_zoeken.client import get_client as get_zoeken_client
from woo_publications.publications.constants import PublicationStatusOptions

from .models import Document, Publication, Topic

logger = logging.getLogger(__name__)


@app.task
def process_source_document(*, document_id: int, base_url: str) -> None:
    """
    Retrieve and process the source document for the given Document instance.

    The source URL stored in the document instance is retrieved and the metadata
    processed. We create a matching document in our own Documents API persistence
    layer. Finally, we download the binary content of the specified document and upload
    it + mark the document upload as completed.

    Any intermediate stage/checkpoint is persisted to the database so that we can
    recover from errors if needed.
    """
    document = Document.objects.get(pk=document_id)
    if document.upload_complete:
        return

    assert (document_url := document.source_url), (
        "The document must have a source URL to retrieve"
    )

    # always look up the source document - if we get here, it means that we at least
    # have some more file part upload work to do
    service = Service.get_service(document_url)
    assert service is not None
    with get_documents_client(service) as source_documents_client:
        source_document = source_documents_client.retrieve_document(url=document_url)

        # Make sure that we have a persisted version of the source document metadata
        if document.document_uuid is None:
            assert document.document_service is None
            # ensure that our metadata properties match the metadata from the source
            # document. The properties get saved via the ``register_in_documents_api``
            # method.
            document.creatiedatum = source_document.creation_date
            document.bestandsformaat = source_document.content_type
            document.bestandsnaam = source_document.file_name
            document.bestandsomvang = source_document.file_size or 0
            # now, create the metadata document for our own storage needs. This is
            # almost a copy of the source document.
            document.register_in_documents_api(
                build_absolute_uri=lambda abs_path: urljoin(base_url, abs_path[1:])
            )
        else:
            assert document.zgw_document is None
            with get_documents_client(document.document_service) as client:
                zgw_document = client.retrieve_document(uuid=document.document_uuid)
            document.zgw_document = zgw_document

        assert document.zgw_document is not None

        # There must be *some* parts left to upload, or the upload_complete flag would
        # have been set.
        parts = document.zgw_document.file_parts
        assert source_document.file_size is not None
        downloader = PartsDownloader(
            parts=parts,
            file_name=document.bestandsnaam,
            total_size=source_document.file_size,
        )
        parts_and_files = downloader.download(
            client=source_documents_client,
            source_url=document.source_url,
        )

        # we now have part metadata and actual file-like objects for each part that
        # we can upload
        with get_documents_client(document.document_service) as client:
            for part, part_file in parts_and_files:
                # this line is hard to test, since the documents API determines the part
                # sizes
                if part.completed:  # pragma: no cover
                    continue

                part_file.seek(0)
                client.proxy_file_part_upload(
                    part_file,
                    file_part_uuid=part.uuid,
                    lock=document.lock,
                )

            document.check_and_mark_completed(client)


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

    with get_zoeken_client(service) as client:
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
        not force
        and (current_status := document.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        logger.info(
            "Document has publication status %s, skipping index removal.",
            current_status,
        )
        return

    with get_zoeken_client(service) as client:
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

    with get_zoeken_client(service) as client:
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

    with get_zoeken_client(service) as client:
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

    with get_zoeken_client(service) as client:
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

    with get_zoeken_client(service) as client:
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

    with get_zoeken_client(service) as client:
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
