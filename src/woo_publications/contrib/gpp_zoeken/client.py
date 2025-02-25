"""
Client implementation for GPP-Zoeken.
"""

from __future__ import annotations

import logging

from zgw_consumers.client import build_client
from zgw_consumers.models import Service
from zgw_consumers.nlx import NLXClient

from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.models import Document, Publication

from .typing import (
    IndexDocumentBody,
    IndexDocumentResponse,
    IndexPublicationBody,
    IndexPublicationResponse,
    PublicationInformatieCategorie,
    RemoveDocumentFromIndexResponse,
    RemovePublicationFromIndexResponse,
)

__all__ = ["get_client"]

logger = logging.getLogger(__name__)


def get_client(service: Service) -> GPPSearchClient:
    return build_client(service=service, client_factory=GPPSearchClient)


def get_publication_information_categories(
    publication: Publication,
) -> list[PublicationInformatieCategorie]:
    qs = publication.informatie_categorieen.values("uuid", "naam")
    return [{"naam": item["naam"], "uuid": str(item["uuid"])} for item in qs]


class GPPSearchClient(NLXClient):
    def index_document(self, document: Document) -> str:
        """
        Synchronize a document to the search index.
        """
        if document.publicatiestatus != PublicationStatusOptions.published:
            raise ValueError("The document does not have 'published' status!")

        body: IndexDocumentBody = {
            "uuid": str(document.uuid),
            "publicatie": str(document.publicatie.uuid),
            "publisher": {
                "uuid": str(document.publicatie.publisher.uuid),
                "naam": document.publicatie.publisher.naam,
            },
            "informatieCategorieen": get_publication_information_categories(
                document.publicatie
            ),
            "identifier": document.identifier,
            "officieleTitel": document.officiele_titel,
            "verkorteTitel": document.verkorte_titel,
            "omschrijving": document.omschrijving,
            "creatiedatum": document.creatiedatum.isoformat(),
            "registratiedatum": document.registratiedatum.isoformat(),
            "laatstGewijzigdDatum": document.laatst_gewijzigd_datum.isoformat(),
        }

        response = self.post("documenten", json=body)
        response.raise_for_status()

        response_data: IndexDocumentResponse = response.json()
        return response_data["taskId"]

    def remove_document_from_index(self, document: Document) -> str:
        if document.publicatiestatus == PublicationStatusOptions.published:
            raise ValueError("The document has 'published' status!")

        response = self.delete(f"documenten/{document.uuid}")
        response.raise_for_status()

        response_data: RemoveDocumentFromIndexResponse = response.json()
        return response_data["taskId"]

    def index_publication(self, publication: Publication):
        """
        Synchronize a publication to the search index.
        """

        if publication.publicatiestatus != PublicationStatusOptions.published:
            raise ValueError("The publication does not have 'published' status!")

        body: IndexPublicationBody = {
            "uuid": str(publication.uuid),
            "publisher": {
                "uuid": str(publication.publisher.uuid),
                "naam": publication.publisher.naam,
            },
            "informatieCategorieen": get_publication_information_categories(
                publication
            ),
            "officieleTitel": publication.officiele_titel,
            "verkorteTitel": publication.verkorte_titel,
            "omschrijving": publication.omschrijving,
            "registratiedatum": publication.registratiedatum.isoformat(),
            "laatstGewijzigdDatum": publication.laatst_gewijzigd_datum.isoformat(),
        }

        response = self.post("publicaties", json=body)
        response.raise_for_status()

        response_data: IndexPublicationResponse = response.json()
        return response_data["taskId"]

    def remove_publication_from_index(self, publication: Publication) -> str:
        if publication.publicatiestatus == PublicationStatusOptions.published:
            raise ValueError("The publication has 'published' status!")

        response = self.delete(f"publicaties/{publication.uuid}")
        response.raise_for_status()

        response_data: RemovePublicationFromIndexResponse = response.json()
        return response_data["taskId"]
