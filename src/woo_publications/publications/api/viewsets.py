import logging
from collections.abc import Iterable
from functools import partial
from typing import override
from uuid import UUID

from django.db import transaction
from django.http import StreamingHttpResponse
from django.utils.http import content_disposition_header
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from requests import RequestException
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from woo_publications.api.exceptions import BadGateway
from woo_publications.contrib.documents_api.client import get_client
from woo_publications.logging.service import (
    AuditTrailViewSetMixin,
    audit_api_download,
    extract_audit_parameters,
)

from ..constants import PublicationStatusOptions
from ..models import Document, Publication
from ..tasks import (
    index_document,
    index_publication,
    remove_document_from_index,
    remove_publication_from_index,
)
from .filters import DocumentFilterSet, PublicationFilterSet
from .serializers import (
    DocumentSerializer,
    DocumentStatusSerializer,
    DocumentUpdateSerializer,
    FilePartSerializer,
    PublicationSerializer,
)

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE = (
    8_192  # read 8 kB into memory at a time when downloading from upstream
)


@extend_schema(tags=["Documenten"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available documents."),
        description=_("Returns a paginated result list of existing documents."),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific document."),
        description=_("Retrieve a specific document."),
    ),
    update=extend_schema(
        summary=_("Update the metadata of a specific document."),
        description=_("Update the metadata of a specific document."),
    ),
    partial_update=extend_schema(
        summary=_("Update the metadata of a specific document partially."),
        description=_("Update the metadata of a specific document partially."),
    ),
    create=extend_schema(
        summary=_("Register a document's metadata."),
        description=_(
            "Creating a document results in the registration of the metadata and "
            "prepares the client for the upload of the binary data.\n\n"
            "The document (metadata) is immediately registered in the underlying "
            "Documents API, and you receive an array of `bestandsdelen` in the "
            "response data to upload the actual binary data of the document.\n\n"
            "Note that the record in the underlying Documents API remains locked until "
            "all file parts have been provided.\n\n"
            "**NOTE**\n"
            "This requires the global configuration to be set up via the admin "
            "interface. You must:\n\n"
            "* configure and select the Documents API to use\n"
            "* specify the organisation RSIN for the created documents"
        ),
    ),
)
class DocumentViewSet(
    AuditTrailViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = Document.objects.order_by("-creatiedatum")
    serializer_class = DocumentSerializer
    filterset_class = DocumentFilterSet
    lookup_field = "uuid"
    lookup_value_converter = "uuid"

    @override
    @transaction.atomic()
    def perform_create(self, serializer):
        """
        Register the metadata in the database and create the record in the Documents API.
        """
        super().perform_create(serializer)
        assert serializer.instance is not None
        woo_document = serializer.instance
        assert isinstance(woo_document, Document)
        woo_document.register_in_documents_api(
            build_absolute_uri=self.request.build_absolute_uri,
        )

    @transaction.atomic()
    def perform_update(self, serializer):
        document = serializer.instance
        assert document is not None
        original_status = document.publicatiestatus
        super().perform_update(serializer)
        new_status = document.publicatiestatus

        match (original_status, new_status):
            # from anything to published -> reindex (even if no status is changed,
            # update the metadata)
            case (_, PublicationStatusOptions.published):
                transaction.on_commit(
                    partial(index_document.delay, document_id=document.pk)
                )
            # from published to anything else -> remove from index
            case (
                PublicationStatusOptions.published,
                PublicationStatusOptions.revoked | PublicationStatusOptions.concept,
            ):
                transaction.on_commit(
                    partial(remove_document_from_index.delay, document_id=document.pk)
                )
            case _:  # pragma: no cover
                pass

    def get_serializer_class(self):
        action = getattr(self, "action", None)
        if action in ["update", "partial_update"]:
            return DocumentUpdateSerializer
        return super().get_serializer_class()

    @extend_schema(
        summary=_("Upload file part"),
        description=_(
            "Send the binary data for a file part to perform the actual file upload. "
            "The response data of the document create endpoints returns the list of "
            "expected file parts, pointing to this endpoint. The client must split "
            "the binary file in the expected part sizes and then upload each chunk "
            "individually.\n\n"
            "Once all file parts for the document are received, the document will be "
            "automatically unlocked in the Documents API and ready for use.\n\n"
            "**NOTE** this endpoint expects `multipart/form-data` rather than JSON to "
            "avoid the base64 encoding overhead."
        ),
        responses={200: DocumentStatusSerializer},
    )
    @action(
        detail=True,
        methods=["put"],
        serializer_class=FilePartSerializer,
        parser_classes=(MultiPartParser,),
        url_path="bestandsdelen/<uuid:part_uuid>",
        url_name="filepart-detail",
    )
    def file_part(self, request: Request, part_uuid: UUID, *args, **kwargs) -> Response:
        document = self.get_object()
        assert isinstance(document, Document)
        serializer = FilePartSerializer(
            data=request.data,
            context={"request": request, "view": self},
        )
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data["inhoud"]
        try:
            is_completed = document.upload_part_data(uuid=part_uuid, file=file)
        except RequestException as exc:
            # we can only handle HTTP 400 responses
            if (_response := exc.response) is None:
                raise
            if _response.status_code != 400:
                raise
            # XXX: should we transform these error responses?
            raise serializers.ValidationError(detail=_response.json()) from exc

        if is_completed:
            transaction.on_commit(
                partial(index_document.delay, document_id=document.pk)
            )

        response_serializer = DocumentStatusSerializer(
            instance={"document_upload_voltooid": is_completed}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

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
                response=(200,),
            ),
            OpenApiParameter(
                name="Content-Disposition",
                type=str,
                location=OpenApiParameter.HEADER,
                description=_(
                    "Marks the file as attachment and includes the filename."
                ),
                response=(200,),
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_name="download")
    def download(self, request: Request, *args, **kwargs) -> StreamingHttpResponse:
        document = self.get_object()
        assert isinstance(document, Document)

        assert (
            document.document_service is not None
        ), "Document must exist in upstream API"

        endpoint = f"enkelvoudiginformatieobjecten/{document.document_uuid}/download"
        with get_client(document.document_service) as client:
            upstream_response = client.get(endpoint, stream=True)

            if (_status := upstream_response.status_code) != status.HTTP_200_OK:
                logger.warning(
                    "Streaming of file contents (ID: %s) fails. Status code: %r.",
                    document.document_uuid,
                    _status,
                    extra={
                        "document_id": document.document_uuid,
                        "api_root": client.base_url,
                    },
                )
                raise BadGateway(detail=_("Could not download from the upstream."))

            # generator that produces the chunks
            streaming_content: Iterable[bytes] = (
                chunk
                for chunk in upstream_response.iter_content(
                    chunk_size=DOWNLOAD_CHUNK_SIZE
                )
                if chunk
            )

            response = StreamingHttpResponse(
                streaming_content,
                # TODO: if we have format information, we can use it, but that's not part
                # of BB-MVP
                content_type="application/octet-stream",
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


@extend_schema(tags=["Publicaties"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available publications."),
        description=_("Returns a paginated result list of existing publications."),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific publication."),
        description=_("Retrieve a specific publication."),
    ),
    create=extend_schema(
        summary=_("Create a publication."),
        description=_("Create a publication."),
    ),
    partial_update=extend_schema(
        summary=_("Update a publication partially."),
        description=_("Update a publication partially."),
    ),
    update=extend_schema(
        summary=_("Update a publication entirely."),
        description=_("Update a publication entirely."),
    ),
    destroy=extend_schema(
        summary=_("Destroy a publication."),
        description=_("Destroy a publication."),
    ),
)
class PublicationViewSet(AuditTrailViewSetMixin, viewsets.ModelViewSet):
    queryset = Publication.objects.order_by("-registratiedatum")
    serializer_class = PublicationSerializer
    filterset_class = PublicationFilterSet
    lookup_field = "uuid"
    lookup_value_converter = "uuid"

    @transaction.atomic()
    def perform_create(self, serializer):
        super().perform_create(serializer)
        assert serializer.instance is not None
        publication = serializer.instance
        assert publication is not None
        transaction.on_commit(
            partial(index_publication.delay, publication_id=publication.pk)
        )

    @transaction.atomic()
    def perform_update(self, serializer):
        publication = serializer.instance
        assert publication is not None
        original_status = publication.publicatiestatus
        super().perform_update(serializer)
        new_status = publication.publicatiestatus

        match (original_status, new_status):
            # from anything to published -> reindex (even if no status is changed,
            # update the metadata)
            case (_, PublicationStatusOptions.published):
                transaction.on_commit(
                    partial(index_publication.delay, publication_id=publication.pk)
                )
            # from published to anything else -> remove from index
            case (
                PublicationStatusOptions.published,
                PublicationStatusOptions.revoked | PublicationStatusOptions.concept,
            ):
                transaction.on_commit(
                    partial(
                        remove_publication_from_index.delay,
                        publication_id=publication.pk,
                    )
                )
            case _:  # pragma: no cover
                pass
