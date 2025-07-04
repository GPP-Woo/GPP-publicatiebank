import logging
from io import BytesIO
from typing import Literal, assert_never
from urllib.parse import urljoin
from uuid import UUID

from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile,
    UploadedFile,
)

from furl import furl
from zgw_consumers.models import Service

from woo_publications.celery import app
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.documents_api.client import (
    FilePart,
    get_client as get_documents_client,
)
from woo_publications.contrib.gpp_zoeken.client import get_client as get_zoeken_client
from woo_publications.publications.constants import PublicationStatusOptions

from .models import Document, Publication, Topic

logger = logging.getLogger(__name__)

TEN_MB = 10 * 1024 * 1024


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

        # Check if we have file parts to upload/complete. If there are, download the
        # source document first.
        if parts := document.zgw_document.file_parts:
            file_size = source_document.file_size
            assert file_size is not None

            def _file_factory(index: int, part_size: int) -> UploadedFile:
                name = f"{document.bestandsnaam}_part{index}.bin"
                assert file_size is not None
                # use in-memory files for files smaller than 10MB
                if file_size <= TEN_MB:  # 10 MB
                    return InMemoryUploadedFile(
                        file=BytesIO(),
                        field_name=None,
                        name=name,
                        content_type=None,
                        size=part_size,
                        charset=None,
                    )
                else:
                    return TemporaryUploadedFile(
                        name=name,
                        content_type=None,
                        size=file_size,
                        charset=None,
                    )

            # furl keeps the query string parameters when modifying the URL path like
            # this
            download_url = furl(document.source_url) / "download"
            download_response = source_documents_client.get(
                str(download_url),
                stream=True,
            )
            download_response.raise_for_status()

            _part: FilePart = parts[0]
            _files: list[UploadedFile] = [_file_factory(index=0, part_size=_part.size)]
            _part_bytes_written = 0

            for chunk in download_response.iter_content(chunk_size=8_192):  # 8kb chunks
                _part_index = parts.index(_part)
                _file = _files[_part_index]

                # _num_bytes_left_to_write may be larger than chunk size, but that's
                # okay, it just means that the bytes for next part is empty and we don't
                # prepare the next file yet.
                _num_bytes_left_to_write = _part.size - _part_bytes_written
                for_current_part = chunk[:_num_bytes_left_to_write]
                # we only need to write to the part if we need to actually process it
                if not _part.completed:
                    _file.write(for_current_part)
                _part_bytes_written += len(for_current_part)

                # if this chunk has data for the next part, prepare the next file
                for_next_part = chunk[_num_bytes_left_to_write:]
                if next_part_size := len(for_next_part):
                    _next_part_index = _part_index + 1
                    _part = parts[_next_part_index]
                    _file = _file_factory(index=_next_part_index, part_size=_part.size)
                    _files.append(_file)
                    _part_bytes_written = next_part_size
                # this chunk finishes the part exactly, initialize the next part
                elif _part_bytes_written == _part.size and _part is not parts[-1]:
                    _next_part_index = _part_index + 1
                    _part = parts[_next_part_index]
                    _file = _file_factory(index=_next_part_index, part_size=_part.size)
                    _files.append(_file)
                    _part_bytes_written = 0

            assert len(_files) == len(parts)

            # we now have part metadata and actual file-like objects for each part that
            # we can upload
            with get_documents_client(document.document_service) as client:
                for part, part_file in zip(parts, _files, strict=True):
                    if part.completed:
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
