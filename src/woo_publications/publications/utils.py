from uuid import UUID

from django.http import HttpRequest
from django.urls import reverse_lazy


def absolute_document_download_uri(request: HttpRequest, document_uuid: UUID) -> str:
    """
    Creates the absolute document URI for the document-download endpoint.
    """
    lazy_document_download_url = reverse_lazy(
        "api:document-download", kwargs={"uuid": str(document_uuid)}
    )
    return request.build_absolute_uri(lazy_document_download_url) or ""
