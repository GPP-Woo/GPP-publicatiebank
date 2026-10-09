from __future__ import annotations

from uuid import UUID

from django.utils.translation import gettext as _

import sentry_sdk
from requests.exceptions import RequestException
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.client import build_client
from zgw_consumers.models import Service
from zgw_consumers.nlx import NLXClient

__all__ = ["CatalogiAPIError", "get_client"]

from .typing import IOT, IOTBody, IOTListResponse, IOTResponse


def get_client(service: Service) -> CatalogiClient:
    return build_client(service, client_factory=CatalogiClient)


class CatalogiAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# TODO: fix this ugly way to scrape out the UUID
#  requires change in OpenZaak to add the UUID to the response
def iot_uuid(url: str) -> UUID:
    try:
        uuid = url.rsplit("/", 1)[-1]
        return UUID(uuid)
    except ValueError as err:  # pragma: no cover
        raise CatalogiAPIError(
            message=_("Malformed uuid retrieved from informatieobjecttypen response."),
            status_code=None,
        ) from err


class CatalogiClient(NLXClient):
    """
    Implement interactions with a Catalogi API.
    """

    def create_catalogi(
        self,
        *,
        rsin: str,
    ) -> str:
        body = {
            "domein": "GPP",
            "rsin": rsin,
            # TODO alter this to real data?
            "contactpersoonBeheerNaam": "Unknown",
        }

        try:
            response = self.post("catalogussen", json=body)
            response.raise_for_status()
        except RequestException as err:
            raise CatalogiAPIError(
                message=_("Catalogus couldn't be created."),
                status_code=getattr(
                    getattr(err, "response", None), "status_code", None
                ),
            ) from err

        return response.json()["url"]

    def create_iot(
        self,
        *,
        catalogus: str,
        description: str,
        confidentiality_indication: VertrouwelijkheidsAanduidingen,
    ) -> IOT:
        if iot := self.get_iot_by_description(
            catalogus=catalogus,
            description=description,
        ):
            return iot

        body: IOTBody = {
            "catalogus": catalogus,
            "omschrijving": description[:80],
            # hardcoded dummy data
            "vertrouwelijkheidaanduiding": confidentiality_indication,
            "beginGeldigheid": "2024-09-01",
            "informatieobjectcategorie": "Wet Open Overheid",
        }

        try:
            response = self.post("informatieobjecttypen", json=body)
            response.raise_for_status()
        except RequestException as err:
            raise CatalogiAPIError(
                message=_("Something went wrong while creating IOT."),
                status_code=getattr(
                    getattr(err, "response", None), "status_code", None
                ),
            ) from err

        response_data: IOTResponse = response.json()

        uuid = iot_uuid(response_data["url"])

        iot = IOT(
            uuid=uuid,
            url=response_data["url"],
        )

        try:
            response = self.post(f"informatieobjecttypen/{iot.uuid}/publish", json=body)
            response.raise_for_status()
        except RequestException as err:
            self.destroy_iot(uuid=uuid)
            raise CatalogiAPIError(
                message=_("IOT object couldn't be published."),
                status_code=getattr(
                    getattr(err, "response", None), "status_code", None
                ),
            ) from err

        return iot

    def get_iot_by_description(
        self,
        *,
        catalogus: str,
        description: str,
    ) -> IOT | None:
        try:
            response = self.get(
                "informatieobjecttypen",
                params={
                    "catalogus": catalogus,
                    "omschrijving": description[:80],
                    "status": "definitief",
                },
            )
            response.raise_for_status()
        except RequestException as err:
            raise CatalogiAPIError(
                message=_("Something went wrong while trying to retrieving IOT."),
                status_code=getattr(
                    getattr(err, "response", None), "status_code", None
                ),
            ) from err

        data: IOTListResponse = response.json()

        if data["count"] == 0:
            return

        # for now let's assume that the first match is correct
        # this system will not create IOT's with different start/end
        # dates.
        result: IOTResponse = data["results"][0]

        return IOT(
            uuid=iot_uuid(result["url"]),
            url=result["url"],
        )

    def destroy_iot(self, *, uuid: UUID):
        try:
            response = self.delete(f"informatieobjecttypen/{uuid}")
            response.raise_for_status()
        except RequestException as err:
            if (
                status_code := getattr(
                    getattr(err, "response", None), "status_code", None
                )
            ) and status_code == 404:
                return

            sentry_sdk.capture_exception(err)
            raise CatalogiAPIError(
                message=_("Something went wrong while deleting the IOT."),
                status_code=getattr(
                    getattr(err, "response", None), "status_code", None
                ),
            ) from err
