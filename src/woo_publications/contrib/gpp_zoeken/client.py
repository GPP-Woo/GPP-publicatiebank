"""
Client implementation for GPP-Zoeken.
"""

from __future__ import annotations

import structlog
from zgw_consumers.client import build_client
from zgw_consumers.models import Service
from zgw_consumers.nlx import NLXClient

from woo_publications.publications.constants import PublicationStatusOptions
from woo_publications.publications.models import (
    Document,
    Publication,
    Topic,
)

from .typing import (
    IndexDocumentBody,
    IndexDocumentResponse,
    IndexPublicationBody,
    IndexPublicationResponse,
    IndexTopicBody,
    IndexTopicResponse,
    PublicationInformatieCategorie,
    PublicationTopic,
    RemoveDocumentFromIndexResponse,
    RemovePublicationFromIndexResponse,
    RemoveTopicFromIndexResponse,
)

__all__ = ["get_client"]

logger = structlog.stdlib.get_logger(__name__)


def get_client(service: Service) -> GPPSearchClient:
    return build_client(service=service, client_factory=GPPSearchClient)


def get_publication_information_categories(
    publication: Publication,
) -> list[PublicationInformatieCategorie]:
    qs = publication.informatie_categorieen.values("uuid", "naam")
    return [{"naam": item["naam"], "uuid": str(item["uuid"])} for item in qs]


def get_publication_onderwerpen(
    publication: Publication,
) -> list[PublicationTopic]:
    qs = publication.onderwerpen.values("uuid", "officiele_titel")
    return [
        {"officieleTitel": item["officiele_titel"], "uuid": str(item["uuid"])}
        for item in qs
    ]


def get_publication_identifiers(publication: Publication) -> list[str]:
    return list(publication.publicationidentifier_set.values_list("kenmerk", flat=True))


def get_document_identifiers(document: Document) -> list[str]:
    identifiers = list(
        document.documentidentifier_set.values_list("kenmerk", flat=True)
    )
    if primary_identifier := document.identifier:
        identifiers.insert(0, primary_identifier)
    return identifiers


class GPPSearchClient(NLXClient):
    def index_document(self, document: Document, download_url: str = "") -> str:
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
            "onderwerpen": get_publication_onderwerpen(document.publicatie),
            "informatieCategorieen": get_publication_information_categories(
                document.publicatie
            ),
            "identifiers": get_document_identifiers(document),
            "officieleTitel": document.officiele_titel,
            "verkorteTitel": document.verkorte_titel,
            "omschrijving": document.omschrijving,
            "creatiedatum": document.creatiedatum.isoformat(),
            "registratiedatum": document.registratiedatum.isoformat(),
            "laatstGewijzigdDatum": document.laatst_gewijzigd_datum.isoformat(),
            "gepubliceerdOp": document.gepubliceerd_op.isoformat(),
            "fileSize": document.bestandsomvang,
            "downloadUrl": download_url,
        }

        response = self.post("documenten", json=body)
        response.raise_for_status()

        response_data: IndexDocumentResponse = response.json()
        return response_data["taskId"]

    def remove_document_from_index(
        self, document: Document, force: bool = False
    ) -> str:
        if (
            not force
            and document.publicatiestatus == PublicationStatusOptions.published
        ):
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
            "onderwerpen": get_publication_onderwerpen(publication),
            "informatieCategorieen": get_publication_information_categories(
                publication
            ),
            "identifiers": get_publication_identifiers(publication),
            "officieleTitel": publication.officiele_titel,
            "verkorteTitel": publication.verkorte_titel,
            "omschrijving": publication.omschrijving,
            "registratiedatum": publication.registratiedatum.isoformat(),
            "laatstGewijzigdDatum": publication.laatst_gewijzigd_datum.isoformat(),
            "gepubliceerdOp": publication.gepubliceerd_op.isoformat(),
            "datumBeginGeldigheid": publication.datum_begin_geldigheid.isoformat()
            if publication.datum_begin_geldigheid
            else None,
            "datumEindeGeldigheid": publication.datum_einde_geldigheid.isoformat()
            if publication.datum_einde_geldigheid
            else None,
        }

        response = self.post("publicaties", json=body)
        response.raise_for_status()

        response_data: IndexPublicationResponse = response.json()
        return response_data["taskId"]

    def remove_publication_from_index(
        self, publication: Publication, force: bool = False
    ) -> str:
        if (
            not force
            and publication.publicatiestatus == PublicationStatusOptions.published
        ):
            raise ValueError("The publication has 'published' status!")

        response = self.delete(f"publicaties/{publication.uuid}")
        response.raise_for_status()

        response_data: RemovePublicationFromIndexResponse = response.json()
        return response_data["taskId"]

    def index_topic(self, topic: Topic):
        """
        Synchronize a topic to the search index.
        """

        if topic.publicatiestatus != PublicationStatusOptions.published:
            raise ValueError("The topic does not have 'published' status!")

        body: IndexTopicBody = {
            "uuid": str(topic.uuid),
            "officieleTitel": topic.officiele_titel,
            "omschrijving": topic.omschrijving,
            "registratiedatum": topic.registratiedatum.isoformat(),
            "laatstGewijzigdDatum": topic.laatst_gewijzigd_datum.isoformat(),
        }

        response = self.post("onderwerpen", json=body)
        response.raise_for_status()

        response_data: IndexTopicResponse = response.json()
        return response_data["taskId"]

    def remove_topic_from_index(self, topic: Topic, force: bool = False) -> str:
        if not force and topic.publicatiestatus == PublicationStatusOptions.published:
            raise ValueError("The topic has 'published' status!")

        response = self.delete(f"onderwerpen/{topic.uuid}")
        response.raise_for_status()

        response_data: RemoveTopicFromIndexResponse = response.json()
        return response_data["taskId"]
