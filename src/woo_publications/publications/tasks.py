from typing import Literal, assert_never
from urllib.parse import urljoin
from uuid import UUID

import structlog
from requests import RequestException
from zgw_consumers.models import Service

from woo_publications.accounts.models import User
from woo_publications.celery import app
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import (
    DocumentsAPIError,
    PartsDownloader,
    get_client as get_documents_client,
)
from woo_publications.contrib.gpp_zoeken.client import get_client as get_zoeken_client
from woo_publications.logging.logevent import audit_admin_document_delete
from woo_publications.publications.constants import PublicationStatusOptions

from .models import Document, Publication, Topic

logger = structlog.stdlib.get_logger(__name__)


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
        logger.info("index_task_skipped", reason="no_gpp_search_service_configured")
        return

    document = Document.objects.select_related(
        "publicatie", "publicatie__publisher"
    ).get(pk=document_id)
    log = logger.bind(document_id=str(document.uuid))
    if (
        current_status := document.publicatiestatus
    ) != PublicationStatusOptions.published:
        log.info(
            "index_task_skipped",
            reason="invalid_document_publication_status",
            publication_status=current_status,
        )
        return

    if not document.upload_complete:
        log.info("index_task_skipped", reason="upload_not_complete")
        return

    if (
        not (pub_status := document.publicatie.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        log.info(
            "index_task_skipped",
            reason="invalid_publication_publication_status",
            publication_status=pub_status,
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
            "index_removal_task_skipped", reason="no_gpp_search_service_configured"
        )
        return

    document = Document.objects.get(pk=document_id)
    log = logger.bind(document_id=str(document.uuid))
    if (
        not force
        and (current_status := document.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        log.info(
            "index_removal_task_skipped",
            reason="invalid_document_publication_status",
            publication_status=current_status,
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
        logger.info("index_task_skipped", reason="no_gpp_search_service_configured")
        return

    publication = Publication.objects.get(pk=publication_id)
    log = logger.bind(publication_id=str(publication.uuid))
    if (
        current_status := publication.publicatiestatus
    ) != PublicationStatusOptions.published:
        log.info(
            "index_task_skipped",
            reason="invalid_publication_publication_status",
            publication_status=current_status,
        )
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
            "index_removal_task_skipped", reason="no_gpp_search_service_configured"
        )
        return

    publication = Publication.objects.get(pk=publication_id)
    log = logger.bind(publication_id=str(publication.uuid))
    if (
        not force
        and (current_status := publication.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        log.info(
            "index_removal_task_skipped",
            reason="invalid_publication_publication_status",
            publication_status=current_status,
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
        logger.info("index_task_skipped", reason="no_gpp_search_service_configured")
        return

    topic = Topic.objects.get(pk=topic_id)
    log = logger.bind(topic_id=str(topic.uuid))
    if (current_status := topic.publicatiestatus) != PublicationStatusOptions.published:
        log.info(
            "index_task_skipped",
            reason="invalid_topic_publication_status",
            publication_status=current_status,
        )
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
            "index_removal_task_skipped", reason="no_gpp_search_service_configured"
        )
        return

    topic = Topic.objects.get(pk=topic_id)
    log = logger.bind(topic_id=str(topic.uuid))
    if (
        not force
        and (current_status := topic.publicatiestatus)
        == PublicationStatusOptions.published
    ):
        log.info(
            "index_removal_task_skipped",
            reason="invalid_topic_publication_status",
            publication_status=current_status,
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
    log = logger.bind(model_name=model_name, uuid=str(uuid), force=force)
    if (service := config.gpp_search_service) is None:
        log.info(
            "index_removal_task_skipped", reason="no_gpp_search_service_configured"
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


@app.task
def remove_document_from_documents_api(
    *,
    document_id: int,
    user_id: int,
    service_uuid: UUID,
    document_uuid: UUID,
):
    service = Service.objects.get(uuid=service_uuid)
    user = User.objects.get(id=user_id)

    with get_documents_client(service) as client:
        try:
            client.destroy_document(uuid=document_uuid)
        except DocumentsAPIError:
            logger.exception(
                "destroying_documents_api_document_failed",
                uuid=str(document_uuid),
            )
            audit_admin_document_delete(
                content_object=Document(id=document_id),
                django_user=user,
                service_uuid=service_uuid,
                document_uuid=document_uuid,
            )
            return


@app.task
def update_document_rsin(*, document_id: int, rsin: str):
    document = Document.objects.get(pk=document_id)
    uuid = document.document_uuid

    if not uuid or not document.document_service:
        return

    with get_documents_client(document.document_service) as client:
        lock = document.lock
        if not lock:
            # Lock the document to allow updates.
            lock = client.lock_document(uuid)
            # Save the lock incase something goes wrong during the update
            document.lock = lock
            document.save(update_fields=("lock",))

        try:
            # Perform bronorganisatie update
            client.update_document_bronorganisatie(
                uuid=uuid, source_organisation=rsin, lock=lock
            )
        except RequestException:
            raise
        finally:
            # Unlock the document again
            client.unlock_document(uuid=uuid, lock=lock)
            document.lock = ""
            document.save(update_fields=("lock",))
