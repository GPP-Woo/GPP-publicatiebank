from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, viewsets

from ..models import OrganisationUnit
from .serializers import OrganisationUnitSerializer


@extend_schema(tags=["Organisatie-eenheden"])
@extend_schema_view(
    list=extend_schema(
        summary=_("All available organisation units."),
        description=_(
            "Returns a paginated result list of existing organisation units."
        ),
    ),
    retrieve=extend_schema(
        summary=_("Retrieve a specific organisation unit."),
        description=_("Retrieve a specific organisation unit."),
    ),
    update=extend_schema(
        summary=_("Update the metadata of a specific organisation unit."),
        description=_(
            "Update the metadata of a specific organisation unit."
            "\n\nThe following properties cannot be modified after initial creation:"
            "\n* `identifier`"
        ),
    ),
    partial_update=extend_schema(
        summary=_("Update the metadata of a specific organisation unit partially."),
        description=_(
            "Update the metadata of a specific organisation unit partially."
            "\n\nThe following properties cannot be modified after initial creation:"
            "\n* `identifier`"
        ),
    ),
)
class OrganisationUnitViewSet(
    mixins.UpdateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = OrganisationUnit.objects.order_by("naam")
    lookup_field = "identifier"
    lookup_value_converter = "slug"
    serializer_class = OrganisationUnitSerializer
