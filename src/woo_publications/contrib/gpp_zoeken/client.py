"""
Client implementation for GPP-Zoeken.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from zgw_consumers.client import build_client
from zgw_consumers.models import Service
from zgw_consumers.nlx import NLXClient

from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.models import Document

__all__ = ["get_client"]

logger = logging.getLogger(__name__)


def get_client(service: Service) -> GPPSearchClient:
    return build_client(service=service, client_factory=GPPSearchClient)


class IndexDocumentBody(TypedDict):
    pass


class GPPSearchClient(NLXClient):
    def index_document(self, document: Document) -> None:
        """
        Synchronize a document to the search index.
        """
        if document.publicatiestatus != PublicationStatusOptions.published:
            raise ValueError("The document does not have 'published' status!")

        body: IndexDocumentBody = {}

        response = self.post("zaken", json=body)
        response.raise_for_status()
