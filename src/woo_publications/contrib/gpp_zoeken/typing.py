from typing import TypedDict


class PublicationInformatieCategorie(TypedDict):
    uuid: str
    naam: str


class PublicationTopic(TypedDict):
    uuid: str
    officieleTitel: str


class PublicationPublisher(TypedDict):
    uuid: str
    naam: str


class IndexDocumentBody(TypedDict):
    uuid: str
    publicatie: str
    publisher: PublicationPublisher
    onderwerpen: list[PublicationTopic]
    informatieCategorieen: list[PublicationInformatieCategorie]
    identifiers: list[str]
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    creatiedatum: str  # ISO-8601 date
    registratiedatum: str  # ISO-8601 datetime
    laatstGewijzigdDatum: str  # ISO-8601 datetime
    gepubliceerdOp: str  # ISO-8601 datetime
    fileSize: int | None
    downloadUrl: str


class IndexPublicationBody(TypedDict):
    uuid: str
    publisher: PublicationPublisher
    onderwerpen: list[PublicationTopic]
    informatieCategorieen: list[PublicationInformatieCategorie]
    identifiers: list[str]
    officieleTitel: str
    verkorteTitel: str
    omschrijving: str
    registratiedatum: str  # ISO-8601 datetime
    laatstGewijzigdDatum: str  # ISO-8601 datetime
    gepubliceerdOp: str  # ISO-8601 datetime
    datumBeginGeldigheid: str | None  # ISO-8601 datetime
    datumEindeGeldigheid: str | None  # ISO-8601 datetime


class IndexTopicBody(TypedDict):
    uuid: str
    officieleTitel: str
    omschrijving: str
    registratiedatum: str  # ISO-8601 datetime
    laatstGewijzigdDatum: str  # ISO-8601 datetime


class IndexDocumentResponse(TypedDict):
    taskId: str


class RemoveDocumentFromIndexResponse(TypedDict):
    taskId: str


class IndexPublicationResponse(TypedDict):
    taskId: str


class RemovePublicationFromIndexResponse(TypedDict):
    taskId: str


class IndexTopicResponse(TypedDict):
    taskId: str


class RemoveTopicFromIndexResponse(TypedDict):
    taskId: str
