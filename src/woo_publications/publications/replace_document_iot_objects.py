from woo_publications.config.models import GlobalConfiguration
from woo_publications.publications.models import Document

from .tasks import update_document_informatieobjecttype


def change_document_api_iots():
    config = GlobalConfiguration.get_solo()
    if not config.documents_api_service:
        raise RuntimeError(
            "No documents API configured yet! Set up the global configuration."
        )

    if not config.catalogi_api_service:
        raise RuntimeError(
            "No catalogi API configured yet! Set up the global configuration."
        )

    for document in Document.objects.iterator():
        update_document_informatieobjecttype.delay(
            document_id=document.id, documenttype_url=document.get_iot_url
        )
