from django.db import models
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets

from woo_publications.logging.api_tools import (
    AuditTrailCreateMixin,
    AuditTrailRetrieveMixin,
    AuditTrailUpdateMixin,
)

from ...models import InformationCategory, Organisation, Theme
from ..filters import (
    InformationCategoryFilterSet,
    OrganisationFilterSet,
)
from ..serializers import (
    InformationCategorySerializer,
    OrganisationSerializer,
    ThemeSerializer,
)


@extend_schema(tags=["Informatiecategorieën"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available information categories."),
        description=_(
            "Returns a paginated result list of existing information categories."
        ),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific information category."),
        description=_("Retrieve a specific information category."),
    ),
)
class InformationCategoryViewSet(
    AuditTrailRetrieveMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = InformationCategory.objects.all()
    serializer_class = InformationCategorySerializer
    filterset_class = InformationCategoryFilterSet
    lookup_field = "uuid"
    lookup_value_converter = "uuid"


@extend_schema(tags=["Organisaties"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available organisations."),
        description=_("Returns a paginated result list of existing organisations."),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific organisation."),
        description=_("Retrieve a specific organisation."),
    ),
    create=extend_schema(
        summary=_("Create an organisation."),
        description=_("Create an organisation."),
    ),
    partial_update=extend_schema(
        summary=_("Update an organisation partially."),
        description=_("Update an organisation partially."),
    ),
    update=extend_schema(
        summary=_("Update an organisation entirely."),
        description=_("Update an organisation entirely."),
    ),
)
class OrganisationViewSet(
    # Auditlog mixins
    AuditTrailCreateMixin,
    AuditTrailRetrieveMixin,
    AuditTrailUpdateMixin,
    # DRF model Viewset mixins
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    # Viewset
    viewsets.GenericViewSet,
):
    queryset = Organisation.objects.order_by("pk")
    serializer_class = OrganisationSerializer
    filterset_class = OrganisationFilterSet
    lookup_field = "uuid"
    lookup_value_converter = "uuid"

    def filter_queryset(
        self, queryset: models.QuerySet[Organisation]
    ) -> models.QuerySet[Organisation]:
        # let the default filter backends do their work first
        qs = super().filter_queryset(queryset)
        if self.action == "list" and "is_actief" not in self.request.query_params:
            qs = qs.filter(is_actief=True)
        return qs


@extend_schema(tags=["Themas"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available themes."),
        description=_("Returns a paginated result list of existing themes."),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific theme."),
        description=_("Retrieve a specific theme."),
    ),
)
class ThemeViewSet(AuditTrailRetrieveMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Theme.objects.all().order_by("path")
    serializer_class = ThemeSerializer
    lookup_field = "uuid"
    lookup_value_converter = "uuid"

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        # for list operations, restrict to the root nodes and let the serializer
        # look up the children.
        # See #63 for the ticket to optimize this!
        if self.action == "list":
            qs = qs.filter(depth=1)
        return qs
