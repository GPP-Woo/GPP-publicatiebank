from django.http import StreamingHttpResponse
from django.utils.http import content_disposition_header
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request

from woo_publications.api.exceptions import BadGateway, Conflict
from woo_publications.contrib.documents_api.client import get_client
from woo_publications.logging.service import (
    audit_api_download,
    extract_audit_parameters,
)

from ..models import Document


class DocumentDownloadMixin:
    @extend_schema(
        summary=_("Download the binary file contents"),
        description=_(
            "Download the binary content of the document. The endpoint does not return "
            "JSON data, but instead the file content is streamed.\n\n"
            "You can only download the content of files that are completely uploaded "
            "in the upstream API."
        ),
        responses={
            (status.HTTP_200_OK, "application/octet-stream"): OpenApiResponse(
                description=_("The binary file contents."),
                response=bytes,
            ),
            status.HTTP_409_CONFLICT: OpenApiResponse(
                description=_(
                    "Conflict - the document is not (yet) available for download."
                ),
            ),
            status.HTTP_502_BAD_GATEWAY: OpenApiResponse(
                description=_("Bad gateway - failure to stream content."),
            ),
        },
        parameters=[
            OpenApiParameter(
                name="Content-Length",
                type=str,
                location=OpenApiParameter.HEADER,
                description=_("Total size in bytes of the download."),
                response=[200],
            ),
            OpenApiParameter(
                name="Content-Disposition",
                type=str,
                location=OpenApiParameter.HEADER,
                description=_(
                    "Marks the file as attachment and includes the filename."
                ),
                response=[200],
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_name="download")
    def download(self, request: Request, *args, **kwargs) -> StreamingHttpResponse:
        document = self.get_object()  # pyright: ignore[reportAttributeAccessIssue]
        assert isinstance(document, Document)

        if not document.upload_complete:
            raise Conflict(detail=_("The document upload is not yet completed."))

        assert document.document_service is not None, (
            "Document must exist in upstream API"
        )

        with get_client(document.document_service) as client:
            upstream_response, streaming_content = client.download_document(
                uuid=document.document_uuid
            )

        if upstream_response.status_code != status.HTTP_200_OK:
            raise BadGateway(detail=_("Could not download from the upstream."))

        content_type = (
            "application/octet-stream"
            if document.bestandsformaat == "unknown"
            else document.bestandsformaat
        )

        response = StreamingHttpResponse(
            streaming_content,
            content_type=content_type,
            headers={
                "Content-Length": upstream_response.headers.get(
                    "Content-Length", str(document.bestandsomvang)
                ),
                "Content-Disposition": content_disposition_header(
                    as_attachment=True,
                    filename=document.bestandsnaam,
                ),
                # nginx-specific header that prevents files being buffered, instead
                # they will be sent synchronously to the nginx client.
                "X-Accel-Buffering": "no",
            },
        )

        user_id, user_repr, remarks = extract_audit_parameters(request)
        audit_api_download(
            content_object=document,
            user_id=user_id,
            user_display=user_repr,
            remarks=remarks,
        )

        return response
