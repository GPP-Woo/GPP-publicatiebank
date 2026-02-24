from pathlib import Path

from django.core import serializers

import requests
from glom import PathAccessError, T, glom

from woo_publications.metadata.constants import OrganisationOrigins
from woo_publications.metadata.models import Organisation

MUNICIPALITY_WAARDENLIJST_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_gemeenten_compleet/5/json/"
    "rwc_gemeenten_compleet_5.json"
)
SO_WAARDENLIJST_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_samenwerkingsorganisaties_compleet/3/json/"
    "rwc_samenwerkingsorganisaties_compleet_3.json"
)
OORG_WAARDENLIJST_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_overige_overheidsorganisaties_compleet/13/json/"
    "rwc_overige_overheidsorganisaties_compleet_13.json"
)
CARIBBEAN_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_caribische_openbare_lichamen_compleet/1/json/"
    "rwc_caribische_openbare_lichamen_compleet_1.json"
)
PROVINCE_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_provincies_compleet/1/json/rwc_provincies_compleet_1.json"
)
WATER_BOARD_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_waterschappen_compleet/2/json/rwc_waterschappen_compleet_2.json"
)
ZBO_URL = (
    "https://repository.officiele-overheidspublicaties.nl/waardelijsten/"
    "rwc_zbo_compleet/6/json/rwc_zbo_compleet_6.json"
)

MUNICIPALITY_WAARDENLIJST_TYPE = "https://identifier.overheid.nl/tooi/def/ont/Gemeente"
SO_WAARDENLIJST_TYPE = (
    "https://identifier.overheid.nl/tooi/def/ont/Samenwerkingsorganisatie"
)
OORG_WAARDENLIJST_TYPE = (
    "https://identifier.overheid.nl/tooi/def/ont/Overheidsorganisatie"
)

CARIBBEAN_WAARDENLIJST_TYPE = (
    "https://identifier.overheid.nl/tooi/def/ont/CaribischOpenbaarLichaam"
)
PROVINCE_WAARDENLIJST_TYPE = "https://identifier.overheid.nl/tooi/def/ont/Provincie"
WATER_BOARD_WAARDENLIJST_TYPE = "https://identifier.overheid.nl/tooi/def/ont/Waterschap"
ZBO_WAARDENLIJST_TYPE = "https://identifier.overheid.nl/tooi/def/ont/Zbo"

TYPE_MAPPING = [
    (
        MUNICIPALITY_WAARDENLIJST_URL,
        MUNICIPALITY_WAARDENLIJST_TYPE,
        OrganisationOrigins.municipality_list,
    ),
    (SO_WAARDENLIJST_URL, SO_WAARDENLIJST_TYPE, OrganisationOrigins.so_list),
    (OORG_WAARDENLIJST_URL, OORG_WAARDENLIJST_TYPE, OrganisationOrigins.oorg_list),
    (CARIBBEAN_URL, CARIBBEAN_WAARDENLIJST_TYPE, OrganisationOrigins.caribbean_list),
    (PROVINCE_URL, PROVINCE_WAARDENLIJST_TYPE, OrganisationOrigins.province_list),
    (
        WATER_BOARD_URL,
        WATER_BOARD_WAARDENLIJST_TYPE,
        OrganisationOrigins.water_board_list,
    ),
    (ZBO_URL, ZBO_WAARDENLIJST_TYPE, OrganisationOrigins.zbo_list),
]

SPEC = {
    "identifier": "@id",
    "naam": T["http://www.w3.org/2000/01/rdf-schema#label"][0]["@value"],
}


class OrganisatieWaardenlijstError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def update_organisation(file_path: Path):
    for waardenlijst_url, waardenlijst_type, oorsprong in TYPE_MAPPING:
        try:
            response = requests.get(waardenlijst_url)
        except requests.RequestException as err:
            raise OrganisatieWaardenlijstError(
                f"Could not retrieve the value list data from url `{waardenlijst_url}`."
            ) from err

        try:
            response.raise_for_status()
        except requests.RequestException as err:
            raise OrganisatieWaardenlijstError(
                "Got an unexpected response status code when retrieving the value "
                f"list data from url `{waardenlijst_url}`: {response.status_code}."
            ) from err

        data = response.json()
        if not data:
            raise OrganisatieWaardenlijstError(
                f"Received empty data from value list `{waardenlijst_url}`."
            )

        for waardenlijst in data:
            # filter out all ids that aren't waardenlijsten
            if not waardenlijst["@type"][0] == waardenlijst_type:
                continue

            fields = glom(waardenlijst, SPEC, skip_exc=PathAccessError)
            Organisation.objects.update_or_create(
                identifier=waardenlijst["@id"],
                defaults={**fields, "oorsprong": oorsprong},
            )

    value_list_organisations = Organisation.objects.exclude(
        oorsprong=OrganisationOrigins.custom_entry
    )

    fixture_data = serializers.serialize(
        "json",
        value_list_organisations,
        indent=4,
        use_natural_primary_keys=True,
        fields=(
            "uuid",
            "identifier",
            "naam",
            "oorsprong",
        ),
    )

    with open(file_path, "w") as outfile:
        outfile.write(fixture_data)
