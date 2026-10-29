from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from ...models import InformationCategory, Organisation, Theme
from ..serializers import (
    InformationCategorySerializer,
    OrganisationResearchSerializer,
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
class InformationCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InformationCategory.objects.all()
    serializer_class = InformationCategorySerializer
    authentication_classes = ()
    permission_classes = ()
    pagination_class = None
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
)
class OrganisationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Organisation.objects.filter(is_actief=True).order_by("pk")
    serializer_class = OrganisationResearchSerializer
    authentication_classes = ()
    permission_classes = ()
    pagination_class = None
    lookup_field = "uuid"
    lookup_value_converter = "uuid"


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
class ThemeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Theme.objects.all().order_by("path")
    serializer_class = ThemeSerializer
    authentication_classes = ()
    permission_classes = ()
    pagination_class = None
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
