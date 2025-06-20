from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.core.files import File

from furl import furl
from zgw_consumers.client import build_client
from zgw_consumers.models import Service
from zgw_consumers.nlx import NLXClient

from woo_publications.utils.multipart_encoder import MultipartEncoder

from .typing import EIOCreateBody, EIOCreateResponseBody, EIORetrieveBody

__all__ = ["get_client"]


def get_client(service: Service) -> DocumentenClient:
    return build_client(service, client_factory=DocumentenClient)


@dataclass
class FilePart:
    uuid: UUID
    order: int
    size: int
    url: str = ""


@dataclass
class Document:
    uuid: UUID
    lock: str
    file_parts: list[FilePart]


def _extract_uuid(url: str) -> UUID:
    path = furl(url).path
    last_part = path.segments[-1]
    return UUID(last_part)


class DocumentenClient(NLXClient):
    """
    Implement interactions with a Documenten API.

    Requires Documenten API 1.1+ since we use the large file uploads mechanism.
    """

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

        # translate into the necessary metadata for us to track everything
        file_parts = [
            FilePart(
                uuid=_extract_uuid(part_data["url"]),
                order=part_data["volgnummer"],
                size=part_data["omvang"],
            )
            for part_data in response_data["bestandsdelen"]
        ]

        return Document(
            uuid=_extract_uuid(response_data["url"]),
            lock=response_data["lock"],
            file_parts=file_parts,
        )

    def destroy_document(self, uuid: UUID) -> None:
        response = self.delete(f"enkelvoudiginformatieobjecten/{uuid}")
        response.raise_for_status()

    def proxy_file_part_upload(
        self,
        file: File,
        *,
        file_part_uuid: UUID,
        lock: str,
    ) -> None:
        """
        Proxy the file part upload we received to the underlying Documents API.

        Unfortunately it doesn't seem possible to stream the incoming request directly
        to the Documents API using requests, because we need to send some extra form
        data (the lock ID), and streaming seems to be supported only for just the file
        uploads without additional form data (see
        https://requests.readthedocs.io/en/latest/user/advanced/#streaming-uploads).

        Writing a custom file-like wrapper or generator that produces the raw HTTP
        stream with multipart boundaries is not worth it. If we run into performance
        issues, we can consider httpx, aiohttp or an entirely different solution to
        optimize.
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
        document_detail_response = self.get(
            f"enkelvoudiginformatieobjecten/{document_uuid}"
        )
        document_detail_response.raise_for_status()
        document_detail: EIORetrieveBody = document_detail_response.json()
        return all(
            bestandsdeel["voltooid"]
            for bestandsdeel in document_detail["bestandsdelen"]
        )

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
