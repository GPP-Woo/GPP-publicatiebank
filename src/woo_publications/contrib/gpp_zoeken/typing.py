from typing import List, TypedDict


class PublicationInformatieCategorie(TypedDict):
    uuid: str
    naam: str


class PublicationPublisher(TypedDict):
    uuid: str
    naam: str


class IndexDocumentBody(TypedDict):
    uuid: str
    publicatie: str
    publisher: PublicationPublisher
    identifier: str
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    creatiedatum: str  # ISO-8601 date
    registratiedatum: str  # ISO-8601 datetime
    laatstGewijzigdDatum: str  # ISO-8601 datetime


class IndexPublicationBody(TypedDict):
    uuid: str
    publisher: PublicationPublisher
    informatieCategorieen: List[PublicationInformatieCategorie]
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    registratiedatum: str  # ISO-8601 datetime
    laatstGewijzigdDatum: str  # ISO-8601 datetime


class IndexDocumentResponse(TypedDict):
    taskId: str


class RemoveDocumentFromIndexResponse(TypedDict):
    taskId: str


class IndexPublicationResponse(TypedDict):
    taskId: str
