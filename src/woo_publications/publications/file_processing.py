import os
import shutil
import zipfile
from tempfile import NamedTemporaryFile
from typing import IO, Any
from urllib.parse import urljoin

from django.db import transaction
from django.urls import reverse

import structlog
from celery import chain
from pypdf import PdfWriter

from woo_publications.config.models import GlobalConfiguration

from .constants import PublicationStatusOptions
from .models import Document

logger = structlog.stdlib.get_logger(__name__)


MIN_META = b"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" office:version="1.2">
  <office:meta/>
</office:document-meta>"""


class MetaDataStripError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _sync_files(src: IO[Any], dst: IO[Any]):
    # ensure writer is done
    src.flush()
    os.fsync(src.fileno())

    src.seek(0)
    dst.seek(0)
    dst.truncate(0)

    shutil.copyfileobj(src, dst)
    dst.flush()
    os.fsync(dst.fileno())


def strip_all_files(base_url: str) -> int:
    from .tasks import index_document, strip_metadata

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
        if document.has_to_strip_metadata:
            # Create the full document url.
            download_url = reverse(
                "api:document-download", kwargs={"uuid": str(document.uuid)}
            )
            document_url = urljoin(base_url, download_url)

            # define the strip and index tasks.
            strip_metadata_task = strip_metadata.si(
                document_id=document.pk,
                base_url=base_url,
            )
            index_task = index_document.si(
                document_id=document.pk, download_url=document_url
            )

            # chain the tasks together and call it.
            tasks = chain(strip_metadata_task, index_task)
            transaction.on_commit(tasks.delay)

            # update the counter
            counter += 1

    return counter


def strip_pdf(file: IO[Any]) -> None:
    writer = PdfWriter(file, strict=False, full=False)

    # strip meta data fields
    writer.add_metadata(
        {
            "/Author": "",
            "/Title": "",
            "/Subject": "",
            "/Keywords": "",
        },
    )

    if writer.xmp_metadata:  # pragma: no cover
        writer.xmp_metadata.dc_creator = None
        writer.xmp_metadata.pdf_keywords = None

    writer.write(file)


def strip_open_document(file: IO[Any]):
    file.flush()

    with NamedTemporaryFile(dir=os.path.dirname(file.name), delete=False) as temp:
        stripped_file_name = temp.name

        try:
            with (
                zipfile.ZipFile(file.name) as zin,
                zipfile.ZipFile(temp, "w") as zout,
            ):
                for info in zin.infolist():
                    if info.filename == "meta.xml":
                        zout.writestr(info, MIN_META)
                    else:
                        with zin.open(info) as src, zout.open(info, "w") as dst:
                            shutil.copyfileobj(src, dst, 1024 * 1024)

        except Exception as err:
            os.remove(stripped_file_name)
            raise MetaDataStripError(
                message="Something went wrong while stripping the metadata "
                "of the open document file"
            ) from err

    try:
        with open(stripped_file_name, "rb") as stripped_file:
            _sync_files(stripped_file, file)
    finally:
        os.remove(stripped_file_name)
