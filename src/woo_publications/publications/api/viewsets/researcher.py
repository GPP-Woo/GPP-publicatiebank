from django.utils.translation import gettext_lazy as _

import structlog
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework import viewsets

from woo_publications.api.pagination import CursorPagination

from ...constants import PublicationStatusOptions
from ...models import (
    Document,
    Publication,
    Topic,
)
from ..mixins import DocumentDownloadMixin
from ..serializers.document import (
    DocumentResearcherSerializer,
)
from ..serializers.publication import (
    PublicationResearcherSerializer,
)
from ..serializers.topic import (
    TopicResearcherSerializer,
)

logger = structlog.stdlib.get_logger(__name__)


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
)
class DocumentViewSet(
    DocumentDownloadMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = Document.objects.filter(
        publicatiestatus=PublicationStatusOptions.published,
        publicatie__publicatiestatus=PublicationStatusOptions.published,
        upload_complete=True,
    ).order_by("-creatiedatum")
    serializer_class = DocumentResearcherSerializer
    authentication_classes = ()
    permission_classes = ()
    pagination_class = CursorPagination
    pagination_ordering = "-creatiedatum"
    lookup_field = "uuid"
    lookup_value_converter = "uuid"


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
)
class PublicationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Publication.objects.prefetch_related(
            "eigenaar", "eigenaar_groep", "publicationidentifier_set"
        )
        .filter(publicatiestatus=PublicationStatusOptions.published)
        .order_by("-registratiedatum")
    )
    serializer_class = PublicationResearcherSerializer
    authentication_classes = ()
    permission_classes = ()
    pagination_class = CursorPagination
    pagination_ordering = "-registratiedatum"
    lookup_field = "uuid"
    lookup_value_converter = "uuid"


@extend_schema(tags=["Onderwerpen"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available topics."),
        description=_("Returns a paginated result list of existing topics."),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific topic."),
        description=_("Retrieve a specific topic."),
    ),
)
class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Topic.objects.prefetch_related("publication_set")
        .filter(publicatiestatus=PublicationStatusOptions.published)
        .order_by("-registratiedatum")
    )
    serializer_class = TopicResearcherSerializer
    authentication_classes = ()
    permission_classes = ()
    pagination_class = CursorPagination
    pagination_ordering = "-registratiedatum"
    lookup_field = "uuid"
    lookup_value_converter = "uuid"
