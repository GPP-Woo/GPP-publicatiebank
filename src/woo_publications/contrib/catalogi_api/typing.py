import uuid
from dataclasses import dataclass
from typing import Annotated, NotRequired, TypedDict


@dataclass
class IOT:
    uuid: uuid.UUID
    url: str


class IOTBody(TypedDict):
    catalogus: Annotated[str, "URL reference"]
    omschrijving: str
    vertrouwelijkheidaanduiding: str
    beginGeldigheid: Annotated[str, "ISO-8601 date"]
    eindeGeldigheid: NotRequired[Annotated[str, "ISO-8601 date"] | None]
    informatieobjectcategorie: str
    trefwoord: NotRequired[list[str]]
    omschrijvingGeneriek: NotRequired[dict[str, str]]
    concept: NotRequired[bool]


class IOTResponse(IOTBody):
    url: Annotated[str, "URL reference"]
    besluittypen: list[str]
    zaaktypen: list[str]
    beginObject: Annotated[str, "ISO-8601 date"]
    eindeObject: Annotated[str, "ISO-8601 date"]
