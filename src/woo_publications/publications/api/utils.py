from collections.abc import Iterable, Iterator
from functools import lru_cache, partial
from uuid import UUID

from django.core.files import File
from django.db import transaction
from django.utils.translation import gettext_lazy as _

import structlog
from django_fsm import FSMField, Transition
from requests import Response
from rest_framework import status

from woo_publications.api.exceptions import BadGateway
from woo_publications.contrib.documents_api.client import get_client

from ..models import Document

logger = structlog.stdlib.get_logger(__name__)


DOWNLOAD_CHUNK_SIZE = (
    8_192  # read 8 kB into memory at a time when downloading from upstream
)


@lru_cache
def _get_fsm_help_text(fsm_field: FSMField) -> str:
    _transitions: Iterator[Transition] = fsm_field.get_all_transitions(fsm_field.model)
    transitions = "\n".join(
        f'* `"{transition.source}"` -> `"{transition.target}"`'
        for transition in _transitions
    )
    return _(
        "\n\nThe possible state transitions are: \n\n{transitions}.\n\n"
        "Note that some transitions may be limited by business logic."
    ).format(transitions=transitions)


def download_document(document: Document) -> tuple[Response, Iterable[bytes]]:
    endpoint = f"enkelvoudiginformatieobjecten/{document.document_uuid}/download"
    with get_client(document.document_service) as client:
        upstream_response = client.get(endpoint, stream=True)

        if (_status := upstream_response.status_code) != status.HTTP_200_OK:
            logger.warning(
                "file_contents_streaming_failed",
                document_id=str(document.document_uuid),
                status_code=_status,
                api_root=client.base_url,
            )
            raise BadGateway(detail=_("Could not download from the upstream."))

        # generator that produces the chunks
        streaming_content: Iterable[bytes] = (
            chunk
            for chunk in upstream_response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE)
            if chunk
        )

        return upstream_response, streaming_content


def upload_file_part(
    document: Document, part_uuid: UUID, file: File, base_url: str, document_url: str
) -> bool:
    from ..tasks import index_document

    is_completed = document.upload_part_data(uuid=part_uuid, file=file)

    if is_completed:
        transaction.on_commit(
            partial(
                index_document.delay,
                document_id=document.pk,
                base_url=base_url,
                download_url=document_url,
            )
        )

    return is_completed
