"""
Type definitions for the Documenten API interaction.
"""

from typing import Annotated, Literal, NotRequired, TypedDict

type DocumentStatus = Literal[
    "in_bewerking",
    "ter_vaststelling",
    "definitief",
    "gearchiveerd",
]


class EIOCreateBody(TypedDict):
    """
    The shape of the EnkelvoudigInformatieObject create operation body.

    Not all possible properties are listed, only the required and recommended ones.
    See https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/#specificatie-van-de-documenten-api
    for the standard reference.
    """

    identificatie: Annotated[str, "max 40 chars"]
    bronorganisatie: Annotated[str, "RSIN"]
    informatieobjecttype: Annotated[str, "URL reference"]
    creatiedatum: Annotated[str, "ISO-8601 date"]
    titel: Annotated[str, "[1..200] chars"]
    auteur: Annotated[str, "[1..200] chars"]
    status: DocumentStatus
    formaat: NotRequired[Annotated[str, "mime type"]]
    taal: Literal["dut"]  # other languages can be supported in the future
    bestandsnaam: NotRequired[Annotated[str, "max 255 chars"]]
    inhoud: str | None
    bestandsomvang: int | None
    beschrijving: Annotated[str, "max 1000 chars"]
    indicatieGebruiksrecht: bool


class BestandsDeelMeta(TypedDict):
    url: Annotated[str, "URL reference"]
    volgnummer: int
    omvang: int
    voltooid: bool


class EIOCreateResponseBody(EIOCreateBody):
    url: Annotated[str, "API resource URL"]
    bestandsdelen: list[BestandsDeelMeta]
    lock: str


class EIORetrieveBody(TypedDict):
    # note: incomplete, only documented what we use
    url: Annotated[str, "API resource URL"]
    creatiedatum: Annotated[str, "ISO-8601 date"]
    formaat: NotRequired[Annotated[str, "mime type"]]
    bestandsnaam: NotRequired[Annotated[str, "max 255 chars"]]
    bestandsomvang: NotRequired[int | None]
    bestandsdelen: list[BestandsDeelMeta]
    locked: bool
