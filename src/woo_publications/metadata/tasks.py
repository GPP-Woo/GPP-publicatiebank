from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.celery import app, sentry_exponential_backoff
from woo_publications.config.models import GlobalConfiguration
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client
from woo_publications.metadata.models import InformationCategory


@app.task(bind=True, max_retries=3)
def index_iot(
    self,
    *,
    information_category_id: int,
    confidentiality_indication: VertrouwelijkheidsAanduidingen,
):
    information_category = InformationCategory.objects.get(pk=information_category_id)
    if information_category.iot_uuid and information_category.iot_url:
        return

    try:
        information_category.create_iot_object(confidentiality_indication)
    except CatalogiAPIError as err:
        if err.status_code and 429 <= err.status_code < 503:
            raise self.retry(
                countdown=sentry_exponential_backoff(retries=self.request.retries)
            ) from err

        raise


@app.task(bind=True, max_retries=3)
def update_iot_description(self, *, information_category_id: int):
    config = GlobalConfiguration.get_solo()

    if (service := config.catalogi_api_service) is None or not config.catalogus_url:
        raise RuntimeError(
            "No catalogi API configured yet! Set up the global configuration."
        )

    information_category = InformationCategory.objects.get(pk=information_category_id)
    if not information_category.iot_uuid or not information_category.iot_url:
        return

    try:
        with get_client(service) as client:
            client.update_iot_description(
                uuid=information_category.iot_uuid,
                description=information_category.naam,
            )

    except CatalogiAPIError as err:
        if err.status_code and 429 <= err.status_code < 503:
            raise self.retry(
                countdown=sentry_exponential_backoff(retries=self.request.retries)
            ) from err

        raise
