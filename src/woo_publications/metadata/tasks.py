from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.celery import app
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError
from woo_publications.metadata.models import InformationCategory


@app.task(bind=True, max_retries=3)
def index_iot(
    self,
    *,
    information_category_id: int,
    confidentiality_indication: VertrouwelijkheidsAanduidingen,
):
    information_category = InformationCategory.objects.get(pk=information_category_id)
    try:
        information_category.create_iot_object(confidentiality_indication)
    except CatalogiAPIError as err:
        if err.status_code and 429 <= err.status_code < 503:
            raise self.retry(countdown=30) from err

        raise
