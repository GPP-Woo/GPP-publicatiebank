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
)

__all__ = ["get_client"]

logger = logging.getLogger(__name__)


def get_client(service: Service) -> GPPSearchClient:
    return build_client(service=service, client_factory=GPPSearchClient)


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
            "informatieCategorieen": [
                {
                    "uuid": str(informatiecategorie.uuid),
                    "naam": informatiecategorie.naam,
                }
                for informatiecategorie in publication.informatie_categorieen.all()
            ],
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
