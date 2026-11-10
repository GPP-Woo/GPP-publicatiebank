from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import OuterRef
from django.utils.translation import gettext_lazy as _

import structlog
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework import viewsets

from woo_publications.api.pagination import CursorPagination
from woo_publications.api.permissions import ReuseTokenAuthPermission

from ...constants import PublicationStatusOptions
from ...models import (
    Document,
    Publication,
    Topic,
)
from ..filters import LastModifiedFilterSet
from ..mixins import DocumentDownloadMixin
from ..serializers.document import (
    DocumentReuseSerializer,
)
from ..serializers.publication import (
    PublicationReuseSerializer,
)
from ..serializers.topic import (
    TopicReuseSerializer,
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
    ).order_by("-pk")
    serializer_class = DocumentReuseSerializer
    permission_classes = (ReuseTokenAuthPermission,)
    filterset_class = LastModifiedFilterSet
    pagination_class = CursorPagination
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
        Publication.objects.prefetch_related("publicationidentifier_set")
        .annotate(
            published_topic_uuids=ArraySubquery(
                Topic.objects.filter(
                    publication__pk=OuterRef("pk"),
                    publicatiestatus=PublicationStatusOptions.published,
                )
                .order_by("pk")
                .values("uuid")
            )
        )
        .filter(publicatiestatus=PublicationStatusOptions.published)
        .order_by("-pk")
    )
    serializer_class = PublicationReuseSerializer
    permission_classes = (ReuseTokenAuthPermission,)
    filterset_class = LastModifiedFilterSet
    pagination_class = CursorPagination
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
        .prefetch_related("publication_set")
        .annotate(
            published_publication_uuids=ArraySubquery(
                Publication.objects.filter(
                    onderwerpen=OuterRef("pk"),
                    publicatiestatus=PublicationStatusOptions.published,
                )
                .order_by("pk")
                .values("uuid")
            )
        )
        .order_by("-pk")
    )
    serializer_class = TopicReuseSerializer
    permission_classes = (ReuseTokenAuthPermission,)
    filterset_class = LastModifiedFilterSet
    pagination_class = CursorPagination
    lookup_field = "uuid"
    lookup_value_converter = "uuid"
