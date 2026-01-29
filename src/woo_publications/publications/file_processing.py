import structlog

from ..config.models import GlobalConfiguration
from .constants import PublicationStatusOptions
from .models import Document

logger = structlog.stdlib.get_logger(__name__)


def strip_all_files(base_url: str) -> int:
    from .tasks import strip_pdf

    config = GlobalConfiguration.get_solo()

    assert config.gpp_search_service, "Search API services not configured."

    # counter of the amount of documents that were attempted to be stripped
    counter = 0

    for document in Document.objects.filter(
        publicatiestatus=PublicationStatusOptions.published,
        metadata_gestript_op__isnull=True,
        document_uuid__isnull=False,
        upload_complete=True,
        lock="",
    ):
        if document.is_pdf:
            strip_pdf.delay(document_id=document.pk, base_url=base_url)
            counter += 1

    return counter
