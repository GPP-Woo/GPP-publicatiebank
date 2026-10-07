from __future__ import annotations

from django.db.models import CharField, OuterRef, Subquery

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.celery import app
from woo_publications.contrib.catalogi_api.client import CatalogiAPIError
from woo_publications.metadata.models import InformationCategory
from woo_publications.publications.models import Document
from woo_publications.publications.tasks import update_document_informatieobjecttype

from ..publications.constants import PublicationStatusOptions
from .models import GlobalConfiguration


@app.task(bind=True, max_retries=3)
def sync_information_categories_and_documents_with_catalog_api(
    self,
    *,
    confidentiality_indication: VertrouwelijkheidsAanduidingen,
):
    """
    Task to overwrite the Information Category catalog API fields and
    to overwrite the IOT's from the documents in the Document API.
    """
    config = GlobalConfiguration.get_solo()

    if (service := config.catalogi_api_service) is None:
        raise RuntimeError(
            "No catalogi API configured yet! Set up the global configuration."
        )

    if not config.catalogi_api_service:
        raise RuntimeError(
            "No catalogi API configured yet! Set up the global configuration."
        )

    if not config.default_iot_url:
        raise RuntimeError(
            "The Catalogi API isn't configured fully yet, we are missing some if not "
            "all of the Catalogi API global configuration URLS."
        )

    # If the start of the url is different from the service then we can be assured
    # that it isn't the right URL yet.
    for information_category in InformationCategory.objects.exclude(
        iot_url__startswith=service.api_root
    ):
        try:
            information_category.create_iot_object(confidentiality_indication)
        except CatalogiAPIError as err:
            # Don't raise an error if there is some type of temporary problem
            # with the Category API, this will ensure that the task will be retried,
            # since the IOT url won't match the user defined Category API root.
            if err.status_code and 429 <= err.status_code < 503:
                continue

            raise

    # When all the urls are in sync we can update the IOT's of the documents
    # in the Documents API
    if not InformationCategory.objects.exclude(
        iot_url__startswith=service.api_root
    ).exists():
        change_document_api_iots()
        return

    raise self.retry(countdown=30)


@app.task()
def change_document_api_iots():
    """
    Changes the IOT object from the documents in the Document API based on the IOT URL
    present in the top attached Information Category or default IOT URL defined in the
    global config.
    """

    config = GlobalConfiguration.get_solo()
    if not config.documents_api_service:
        raise RuntimeError(
            "No documents API configured yet! Set up the global configuration."
        )

    if not config.catalogi_api_service:
        raise RuntimeError(
            "No catalogi API configured yet! Set up the global configuration."
        )

    if (default_iot := config.default_iot_url) == "":
        raise RuntimeError(
            "The Catalogi API isn't configured fully yet, we are missing some if not "
            "all of the Catalogi API global configuration URLS."
        )

    informationcategory_iots = (
        InformationCategory.objects.filter(publication__pk=OuterRef("publicatie__pk"))
        .order_by("pk")
        .only("iot_url")
        .values("iot_url")[:1]
    )

    for document in (
        Document.objects.exclude(
            document_uuid=None, publicatiestatus=PublicationStatusOptions.revoked
        )
        .annotate(iot_url=Subquery(informationcategory_iots, output_field=CharField()))
        .iterator()
    ):
        update_document_informatieobjecttype.delay(
            document_id=document.id,
            # Pyright doesn't like annotated fields.
            documenttype_url=document.iot_url or default_iot,  # pyright: ignore[reportAttributeAccessIssue]
        )
