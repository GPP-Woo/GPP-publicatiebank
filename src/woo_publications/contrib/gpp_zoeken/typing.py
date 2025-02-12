from typing import TypedDict


class DocumentPublisher(TypedDict):
    uuid: str
    naam: str


class IndexDocumentBody(TypedDict):
    uuid: str
    publicatie: str
    publisher: DocumentPublisher
    identifier: str
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    creatiedatum: str  # ISO-8601 date
    registratiedatum: str  # ISO-8601 datetime
    laatstGewijzigdDatum: str  # ISO-8601 datetime


class IndexDocumentResponse(TypedDict):
    taskId: str
