from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.celery import app
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client


@app.task(bind=True, max_retries=3)
def index_default_iot(self):
    config = GlobalConfiguration.get_solo()

    if (catalogi := config.catalogus_url) == "":
        raise RuntimeError(
            "No catalog configured yet! Set up the global configuration."
        )

    with get_client(config.catalogi_api_service) as client:
        try:
            iot = client.create_iot(
                description=(
                    "informatieobjecttypen of publications with no information "
                    "category objects."
                ),
                catalogus=catalogi,
                confidentiality_indication=VertrouwelijkheidsAanduidingen.vertrouwelijk,
            )
        except CatalogiAPIError as err:
            if err.status_code and 429 <= err.status_code < 503:
                raise self.retry(countdown=30) from err

            raise

        config.default_iot_url = iot.url
        config.save()
