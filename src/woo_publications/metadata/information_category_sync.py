from pathlib import Path

from django.core import serializers

import requests
from glom import PathAccessError, T, glom

from .constants import INFORMATION_CATEGORY_FIXTURE_FIELDS, InformationCategoryOrigins
from .models import InformationCategory

WAARDENLIJST_URL = "https://repository.officiele-overheidspublicaties.nl/waardelijsten/scw_woo_informatiecategorieen/3/json/scw_woo_informatiecategorieen_3.json"

SPEC = {
    "naam": T["http://www.w3.org/2004/02/skos/core#prefLabel"][0]["@value"],
    "naam_meervoud": T[
        "https://identifier.overheid.nl/tooi/def/ont/prefLabelVoorGroepen"
    ][0]["@value"],
    "definitie": T["http://www.w3.org/2004/02/skos/core#definition"][0]["@value"],
    "order": T["http://www.w3.org/ns/shacl#order"][0]["@value"],
}


class InformatieCategoryWaardenlijstError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def update_information_category(file_path: Path):
    try:
        response = requests.get(WAARDENLIJST_URL)
    except requests.RequestException as err:
        raise InformatieCategoryWaardenlijstError(
            "Could not retrieve the value list data."
        ) from err

    try:
        response.raise_for_status()
    except requests.RequestException as err:
        raise InformatieCategoryWaardenlijstError(
            "Got an unexpected response status code when retrieving the value "
            f"list data: {response.status_code}."
        ) from err

    data = response.json()
    if not data:
        raise InformatieCategoryWaardenlijstError(
            "Received empty data from value list."
        )

    for waardenlijst in data:
        # filter out all ids that aren't waardenlijsten
        if (
            not waardenlijst["@type"][0]
            == "http://www.w3.org/2004/02/skos/core#Concept"
        ):
            continue

        fields = glom(waardenlijst, SPEC, skip_exc=PathAccessError)
        InformationCategory.objects.update_or_create(
            identifier=waardenlijst["@id"],
            defaults={**fields, "oorsprong": InformationCategoryOrigins.value_list},
        )

    value_list_information_categories = InformationCategory.objects.filter(
        oorsprong=InformationCategoryOrigins.value_list
    )

    fixture_data = serializers.serialize(
        "json",
        value_list_information_categories,
        indent=4,
        use_natural_primary_keys=True,
        fields=INFORMATION_CATEGORY_FIXTURE_FIELDS,
    )

    with open(file_path, "w") as outfile:
        outfile.write(fixture_data)
