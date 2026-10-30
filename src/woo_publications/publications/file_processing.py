import os
import shutil
import zipfile
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from typing import IO
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction
from django.urls import reverse

import pikepdf
import structlog
from celery import chain
from lxml import html
from santanico import RtfStreamFilter

from woo_publications.config.models import GlobalConfiguration

from .constants import PublicationStatusOptions
from .models import Document

logger = structlog.stdlib.get_logger(__name__)


MIN_OPEN_DOCUMENT_META = b"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0" office:version="1.2">
  <office:meta/>
</office:document-meta>"""

MIN_MS_OFFICE_DOCUMENT_CORE_META = b"""
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties
    xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:dcmitype="http://purl.org/dc/dcmitype/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
</cp:coreProperties>""".strip()

MIN_MS_OFFICE_DOCUMENT_CUSTOM_META = b"""
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties
    xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
    xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
</Properties>""".strip()

assert not MIN_MS_OFFICE_DOCUMENT_CORE_META.startswith(b"\n")
assert not MIN_MS_OFFICE_DOCUMENT_CUSTOM_META.startswith(b"\n")

DEFAULT_CHUNK_SIZE = 1024 * 1024


class MetaDataStripError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


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
        lock="",
    ).iterator():
        if document.has_to_strip_metadata:
            # Create the full document url.
            download_url = reverse(
                "standard:document-download", kwargs={"uuid": str(document.uuid)}
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


@contextmanager
def spooled(chunks: Iterable[bytes]) -> Generator[IO[bytes]]:
    with SpooledTemporaryFile(max_size=DEFAULT_CHUNK_SIZE * 8) as f:
        for chunk in chunks:
            f.write(chunk)
        f.seek(0)
        yield f


def strip_pdf(chunks: Iterable[bytes], dst: IO[bytes]) -> None:
    with spooled(chunks) as src:
        try:
            with pikepdf.open(src) as pdf:  # pyright:ignore[reportArgumentType]
                if "/Info" in pdf.trailer:
                    del pdf.trailer["/Info"]

                if "/Metadata" in pdf.Root:
                    del pdf.Root["/Metadata"]

                pdf.save(dst)  # pyright:ignore[reportArgumentType]

        except Exception as err:
            raise MetaDataStripError(
                message="Something went wrong while stripping the metadata of the PDF "
                "file"
            ) from err


def strip_open_document(chunks: Iterable[bytes], dst: IO[bytes]) -> None:
    with spooled(chunks) as src:
        try:
            with (
                zipfile.ZipFile(src) as zin,
                zipfile.ZipFile(dst, "w") as zout,
            ):
                for info in zin.infolist():
                    if info.filename == "meta.xml":
                        zout.writestr(info, MIN_OPEN_DOCUMENT_META)
                    else:
                        with (
                            zin.open(info) as member_in,
                            zout.open(info, "w") as member_out,
                        ):
                            shutil.copyfileobj(
                                member_in, member_out, DEFAULT_CHUNK_SIZE
                            )

        except Exception as err:
            raise MetaDataStripError(
                message="Something went wrong while stripping the metadata "
                "of the open document file"
            ) from err


def strip_ms_office_document(chunks: Iterable[bytes], dst: IO[bytes]) -> None:
    with spooled(chunks) as src:
        try:
            with (
                zipfile.ZipFile(src) as zin,
                zipfile.ZipFile(dst, "w") as zout,
            ):
                for info in zin.infolist():
                    if info.filename == "docProps/core.xml":
                        zout.writestr(info, MIN_MS_OFFICE_DOCUMENT_CORE_META)
                    elif info.filename == "docProps/custom.xml":
                        zout.writestr(info, MIN_MS_OFFICE_DOCUMENT_CUSTOM_META)
                    else:
                        with (
                            zin.open(info) as member_in,
                            zout.open(info, "w") as member_out,
                        ):
                            shutil.copyfileobj(
                                member_in, member_out, DEFAULT_CHUNK_SIZE
                            )

        except Exception as err:
            raise MetaDataStripError(
                message="Something went wrong while stripping the metadata "
                "of the MS document file"
            ) from err


def strip_zip_file(chunks: Iterable[bytes], dst: IO[bytes]) -> None:
    with spooled(chunks) as src:
        try:
            with (
                zipfile.ZipFile(src) as zin,
                zipfile.ZipFile(dst, "w") as zout,
            ):
                for info in zin.infolist():
                    with (
                        zin.open(info) as member_in,
                        zout.open(info, "w") as member_out,
                    ):
                        shutil.copyfileobj(member_in, member_out, DEFAULT_CHUNK_SIZE)

        except Exception as err:
            raise MetaDataStripError(
                message="Something went wrong while stripping the metadata of the "
                "ZIP file"
            ) from err


def strip_html(chunks: Iterable[bytes], dst: IO[bytes]) -> None:
    with spooled(chunks) as src:
        src.seek(0, os.SEEK_END)
        size = src.tell()
        if size > settings.STRIP_METADATA_HTML_MAX_FILE_SIZE:
            raise MetaDataStripError(message="The file is too large for us to process.")
        src.seek(0)

        try:
            tree = html.fromstring(src.read())

            for meta in tree.xpath("//meta"):
                if meta.get("charset"):
                    continue

                meta.getparent().remove(meta)

            stripped_data = html.tostring(tree, pretty_print=True, method="html")
            del tree

            assert isinstance(stripped_data, bytes)
            dst.write(stripped_data)
        except Exception as err:
            raise MetaDataStripError(
                message="Something went wrong while stripping the metadata of the "
                "HTML file"
            ) from err


def strip_rtf_file(chunks: Iterable[bytes], dst: IO[bytes]) -> None:
    filter_ = RtfStreamFilter()

    try:
        for chunk in chunks:
            dst.write(filter_.process_chunk(chunk))
    except Exception as err:
        raise MetaDataStripError(
            message="Something went wrong while stripping the metadata of the RTF file"
        ) from err
