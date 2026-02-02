from urllib.parse import urljoin

from django.db import transaction
from django.urls import reverse

import structlog
from celery import chain

from woo_publications.config.models import GlobalConfiguration

from .constants import PublicationStatusOptions
from .models import Document

logger = structlog.stdlib.get_logger(__name__)


def strip_all_files(base_url: str) -> int:
    from .tasks import index_document, strip_pdf

    config = GlobalConfiguration.get_solo()

    if not config.gpp_search_service:
        raise AssertionError("Search API services not configured.")

    # counter of the amount of documents that were attempted to be stripped
    counter = 0

    for document in Document.objects.filter(
        publicatiestatus=PublicationStatusOptions.published,
        metadata_gestript_op__isnull=True,
        document_uuid__isnull=False,
        upload_complete=True,
        lock="",
    ).iterator():
        if document.is_pdf:
            # Create the full document url.
            download_url = reverse(
                "api:document-download", kwargs={"uuid": str(document.uuid)}
            )
            document_url = urljoin(base_url, download_url)

            # define the strip and index tasks.
            strip_pdf_task = strip_pdf.si(
                document_id=document.pk,
                base_url=base_url,
            )
            index_task = index_document.si(
                document_id=document.pk, download_url=document_url
            )

            # chain the tasks together and call it.
            tasks = chain(strip_pdf_task, index_task)
            transaction.on_commit(tasks.delay)

            # update the counter
            counter += 1

    return counter
