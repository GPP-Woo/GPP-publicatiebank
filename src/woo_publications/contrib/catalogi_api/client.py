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

from .typing import IOT, IOTBody, IOTResponse


def get_client(service: Service) -> CatalogiClient:
    return build_client(service, client_factory=CatalogiClient)


class CatalogiAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


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
        body: IOTBody = {
            "catalogus": catalogus,
            "omschrijving": description,
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

        # TODO: fix this ugly way to scrape out the UUID
        #  requires change in OpenZaak to add the UUID to the response
        try:
            uuid = response_data["url"].rsplit("/", 1)[-1]
            uuid = UUID(uuid)
        except ValueError as err:  # pragma: no cover
            raise CatalogiAPIError(
                message=_(
                    "Malformed uuid retrieved from informatieobjecttypen response."
                ),
                status_code=getattr(
                    getattr(err, "response", None), "status_code", None
                ),
            ) from err

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
