from woo_publications.config.models import GlobalConfiguration
from woo_publications.publications.models import Document

from .tasks import update_document_informatieobjecttype


def change_all_iot():
    config = GlobalConfiguration.get_solo()
    if config.documents_api_service:
        raise RuntimeError(
            "No documents API configured yet! Set up the global configuration."
        )

    if config.catalogi_api_service:
        raise RuntimeError(
            "No catalogi API configured yet! Set up the global configuration."
        )

    for document in Document.objects.iterator():
        update_document_informatieobjecttype.delay(
            document_id=document.id, documenttype_url=document.get_iot_url
        )
