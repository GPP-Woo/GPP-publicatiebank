from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from typing import Protocol
from uuid import UUID

from django.core.files import File
from django.core.files.uploadedfile import (
    InMemoryUploadedFile,
    TemporaryUploadedFile,
    UploadedFile,
)
from django.utils.translation import gettext as _

import sentry_sdk
from furl import furl
from requests import RequestException
from zgw_consumers.client import build_client
from zgw_consumers.models import Service
from zgw_consumers.nlx import NLXClient

from woo_publications.utils.multipart_encoder import MultipartEncoder

from .typing import (
    BestandsDeelMeta,
    EIOCreateBody,
    EIOCreateResponseBody,
    EIORetrieveBody,
)

__all__ = ["DocumentsAPIError", "get_client"]


def get_client(service: Service) -> DocumentenClient:
    return build_client(service, client_factory=DocumentenClient)


class DocumentsAPIError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class FilePart:
    uuid: UUID
    order: int
    size: int
    completed: bool
    url: str = ""


@dataclass
class Document:
    uuid: UUID
    creation_date: date
    content_type: str
    file_name: str
    file_size: int | None
    lock: str
    file_parts: Sequence[FilePart]


def _extract_uuid(url: str) -> UUID:
    path = furl(url).path
    last_part = path.segments[-1]
    return UUID(last_part)


def _to_file_parts(file_part_data: Sequence[BestandsDeelMeta]) -> Sequence[FilePart]:
    return [
        FilePart(
            uuid=_extract_uuid(part_data["url"]),
            order=part_data["volgnummer"],
            size=part_data["omvang"],
            completed=part_data["voltooid"],
        )
        for part_data in file_part_data
    ]


class DocumentenClient(NLXClient):
    """
    Implement interactions with a Documenten API.

    Requires Documenten API 1.1+ since we use the large file uploads mechanism.
    """

    def retrieve_document(self, *, url: str = "", uuid: UUID | None = None) -> Document:
        assert url or uuid
        if not url:
            url = f"enkelvoudiginformatieobjecten/{uuid}"

        response = self.get(url)
        response.raise_for_status()

        response_data: EIORetrieveBody = response.json()

        return Document(
            uuid=_extract_uuid(response_data["url"]),
            creation_date=date.fromisoformat(response_data["creatiedatum"]),
            content_type=response_data.get("formaat", ""),
            file_name=response_data.get("bestandsnaam", ""),
            file_size=response_data.get("bestandsomvang"),
            lock="",
            file_parts=_to_file_parts(response_data["bestandsdelen"]),
        )

    def create_document(
        self,
        *,
        identification: str,
        source_organisation: str,
        document_type_url: str,
        creation_date: date,
        title: str,
        filesize: int,
        filename: str,
        author: str = "WOO registrations",
        content_type: str = "application/octet-stream",
        description: str = "",
    ) -> Document:
        data: EIOCreateBody = {
            "identificatie": identification,
            "bronorganisatie": source_organisation,
            "informatieobjecttype": document_type_url,
            "creatiedatum": creation_date.isoformat(),
            "titel": title,
            "auteur": author,
            "status": "definitief",
            "formaat": content_type,
            "taal": "dut",
            "bestandsnaam": filename,
            # do not post any data, we use the "file parts" upload mechanism
            "inhoud": None,
            "bestandsomvang": filesize,
            "beschrijving": description[:1000],
            "indicatieGebruiksrecht": False,
        }

        response = self.post("enkelvoudiginformatieobjecten", json=data)
        response.raise_for_status()

        response_data: EIOCreateResponseBody = response.json()

        return Document(
            uuid=_extract_uuid(response_data["url"]),
            creation_date=date.fromisoformat(response_data["creatiedatum"]),
            content_type=response_data.get("formaat", ""),
            file_name=response_data.get("bestandsnaam", ""),
            file_size=response_data.get("bestandsomvang"),
            lock=response_data["lock"],
            # translate into the necessary metadata for us to track everything
            file_parts=_to_file_parts(response_data["bestandsdelen"]),
        )

    def update_document_bronorganisatie(
        self, *, uuid: UUID, source_organisation: str, lock: str
    ) -> None:
        response = self.patch(
            f"enkelvoudiginformatieobjecten/{uuid}",
            json={"bronorganisatie": source_organisation, "lock": lock},
        )
        response.raise_for_status()

    def destroy_document(self, uuid: UUID) -> None:
        try:
            response = self.delete(f"enkelvoudiginformatieobjecten/{uuid}")
            response.raise_for_status()
        except RequestException as err:
            if err.response is not None and err.response.status_code == 404:
                return

            sentry_sdk.capture_exception(err)
            raise DocumentsAPIError(
                message=_("Something went wrong while deleting the document.")
            ) from err

    def proxy_file_part_upload(
        self,
        file: File,
        *,
        file_part_uuid: UUID,
        lock: str,
    ) -> None:
        """
        Proxy the file part upload we received to the underlying Documents API.
        """
        # Verified manually that the underlying urllib3 uses 16MB chunks, see
        # urllib3.connection.HTTPConnection.blocksize
        encoder = MultipartEncoder(
            fields={
                "lock": lock,
                "inhoud": ("part.bin", file, "application/octet-stream"),
            }
        )
        response = self.put(
            f"bestandsdelen/{file_part_uuid}",
            data=encoder,
            headers={"Content-Type": encoder.content_type},
        )
        response.raise_for_status()

    def check_uploads_complete(self, *, document_uuid: UUID) -> bool:
        document = self.retrieve_document(
            url=f"enkelvoudiginformatieobjecten/{document_uuid}"
        )
        return all(part.completed for part in document.file_parts)

    def lock_document(self, uuid: UUID) -> str:
        """
        lock the document in the Documents API to enable editing.
        """
        response = self.post(f"enkelvoudiginformatieobjecten/{uuid}/lock")
        response.raise_for_status()

        return response.json()["lock"]

    def unlock_document(self, *, uuid: UUID, lock: str) -> None:
        """
        Unlock the locked document in the Documents API.
        """
        assert lock, "Lock must not be an empty value"
        response = self.post(
            f"enkelvoudiginformatieobjecten/{uuid}/unlock",
            json={"lock": lock},
        )
        response.raise_for_status()


class FileFactory(Protocol):
    def __call__(self, index: int, part_size: int) -> UploadedFile: ...


class PartsDownloader:
    """
    Download the content of a document for the specified parts.

    The binary content of a document is downloaded in streaming mode so that it still
    works in memory-constrained environments. A referenced file could be multiple GB,
    which will quickly exhaust container memory limits when trying to load all of that
    naively into memory.

    Similarly, to *upload* this file content to a Documents API (to persist our own
    copy/version), large files must be uploaded in chunks and the remote API dictates
    the expected file size for each chunk.

    This helper breaks up a large download into the necessary chunks. Small files
    (< 10MB) are loaded in memory, larger files are downloaded to temporary files on
    disk.
    """

    def __init__(
        self,
        parts: Sequence[FilePart],
        file_name: str,
        total_size: int,
        chunk_size=8_192,  # 8 kb
        small_file_size_limit: int = 10 * 1024 * 1024,  # 10MiB limit by default
    ):
        self.parts = parts
        self.file_name = file_name
        self.total_size = total_size
        self.chunk_size = chunk_size
        self.small_file_size_limit = small_file_size_limit

    def _get_file_factory(self) -> FileFactory:
        def _get_name(index: int) -> str:
            return f"{self.file_name}_part{index}.bin"

        def _in_memory_upload_factory(
            index: int, part_size: int
        ) -> InMemoryUploadedFile:
            return InMemoryUploadedFile(
                file=BytesIO(),
                field_name=None,
                name=_get_name(index),
                content_type=None,
                size=part_size,
                charset=None,
            )

        def _temporary_uploaded_file_factory(
            index: int, part_size: int
        ) -> TemporaryUploadedFile:
            return TemporaryUploadedFile(
                name=_get_name(index),
                content_type=None,
                size=part_size,
                charset=None,
            )

        if self.total_size <= self.small_file_size_limit:
            return _in_memory_upload_factory
        return _temporary_uploaded_file_factory

    def download(
        self,
        client: DocumentenClient,
        source_url: str,
    ) -> Iterator[tuple[FilePart, UploadedFile]]:
        """
        Download the file content and create 'uploads' for each file part.

        For completed parts, no actual file content will be written, only incomplete
        parts will actually be processed.
        """
        if not self.parts:
            return zip((), (), strict=True)

        file_factory = self._get_file_factory()

        # initialize the first part to process & prepare the first target file
        files: list[UploadedFile] = [
            file_factory(index=0, part_size=self.parts[0].size)
        ]
        part_index: int = 0
        part_bytes_written: int = 0

        # furl keeps the query string parameters when modifying the URL path like
        # this
        download_url = furl(source_url) / "download"
        # stream and consume the content via iter_content to keep a low enough memory
        # footprint
        download_response = client.get(str(download_url), stream=True)
        download_response.raise_for_status()

        # process the bytes as we download them
        for chunk in download_response.iter_content(chunk_size=self.chunk_size):
            # there must be equal parts and files for this to make sense
            part = self.parts[part_index]
            file = files[part_index]

            # bytes_left_to_write may be larger than chunk size, but that's
            # okay, it just means that the bytes for next part is empty and we don't
            # prepare the next file yet.
            bytes_left_to_write = part.size - part_bytes_written
            for_current_part = chunk[:bytes_left_to_write]

            # we only need to write to the part if we need to actually process it
            if not part.completed:
                file.write(for_current_part)
            elif file.size != 0:
                file.size = 0
            # but always *mark* the bytes as written otherwise we lose our position in
            # the download stream
            part_bytes_written += len(for_current_part)

            # if this chunk has data for the next part, prepare the next file
            for_next_part = chunk[bytes_left_to_write:]
            if for_next_part_size := len(for_next_part):
                part_index += 1
                file = file_factory(
                    index=part_index, part_size=self.parts[part_index].size
                )
                files.append(file)
                file.write(for_next_part)
                part_bytes_written = for_next_part_size

            # this chunk finishes the part exactly, initialize the next part
            elif part_bytes_written == part.size and part is not self.parts[-1]:
                part_index += 1
                file = file_factory(
                    index=part_index, part_size=self.parts[part_index].size
                )
                files.append(file)
                part_bytes_written = 0

        return zip(self.parts, files, strict=True)
