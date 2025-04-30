from typing import Mapping

from django.db import models
from django.utils.translation import gettext_lazy as _


class PublicationStatusOptions(models.TextChoices):
    published = "gepubliceerd", _("Published")
    concept = "concept", _("Concept")
    revoked = "ingetrokken", _("Revoked")


class DocumentActionTypeOptions(models.TextChoices):
    signed = "ondertekening", _("Signed")
    received = "ontvangst", _("Received")
    declared = "vaststelling", _("Declared")


# Taken from PLOOI documenthandelingen on
# https://standaarden.overheid.nl/tooi/waardelijsten/expression?lijst_uri=https%3A%2F%2Fidentifier.overheid.nl%2Ftooi%2Fset%2Fccw_plooi_documenthandelingen%2F2
# and https://repository.officiele-overheidspublicaties.nl/waardelijsten/ccw_plooi_documenthandelingen/2/json/ccw_plooi_documenthandelingen_2.json
DOCUMENT_ACTION_TOOI_IDENTIFIERS: Mapping[DocumentActionTypeOptions, str] = {
    DocumentActionTypeOptions.signed: "https://identifier.overheid.nl/tooi/def/thes/kern/c_e1ec050e",
    DocumentActionTypeOptions.received: "https://identifier.overheid.nl/tooi/def/thes/kern/c_dfcee535",
    DocumentActionTypeOptions.declared: "https://identifier.overheid.nl/tooi/def/thes/kern/c_641ecd76",
}

# sanity check
assert all(
    value in DOCUMENT_ACTION_TOOI_IDENTIFIERS for value in DocumentActionTypeOptions
), "Not all document action types are mapped1"
