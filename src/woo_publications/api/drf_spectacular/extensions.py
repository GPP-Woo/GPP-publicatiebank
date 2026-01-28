from inspect import isclass

from drf_spectacular.contrib.django_filters import DjangoFilterExtension
from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.plumbing import (
    build_array_type,
    build_basic_type,
    build_parameter_type,
)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from woo_publications.api.utils import underscore_to_camel

from ..permissions import AuditHeaderPermission
from .headers import ALL_AUDIT_PARAMETERS


class CustomFilterExtension(DjangoFilterExtension):
    """
    Custom extension to address shortcomings of the default extension.

    * Camelizes the filter parameters
    * Targets the filter fields that produce warnings because the type can't be
      auto-detected.
    """

    priority = 1

    def get_schema_operation_parameters(
        self, auto_schema, *args, **kwargs
    ):  # pragma: no cover
        """
        camelize query parameters
        """
        parameters = super().get_schema_operation_parameters(
            auto_schema, *args, **kwargs
        )
        for parameter in parameters:
            parameter["name"] = underscore_to_camel(parameter["name"])
        return parameters

    def resolve_filter_field(
        self, auto_schema, model, filterset_class, field_name, filter_field
    ):
        from woo_publications.publications.api.filters import (
            PublicationFilterSet,
            TopicFilterSet,
        )

        match field_name:
            case "publicaties" | "onderwerpen" if filterset_class in (
                TopicFilterSet,
                PublicationFilterSet,
            ):
                schema = build_basic_type(OpenApiTypes.UUID)
                assert schema is not None
                return [
                    build_parameter_type(
                        name=field_name,
                        required=filter_field.extra["required"],
                        location=OpenApiParameter.QUERY,
                        description=self._get_field_description(filter_field, None),
                        schema=build_array_type(schema),
                        enum=None,
                        explode=False,
                        style="form",
                    )
                ]
            case _:
                pass

        return super().resolve_filter_field(
            auto_schema, model, filterset_class, field_name, filter_field
        )


class AuditHeadersExtension(OpenApiViewExtension):
    target_class = "rest_framework.views.APIView"
    match_subclasses = True
    priority = 1

    def view_replacement(self) -> type[APIView]:
        view_cls = self.target
        assert isclass(view_cls) and issubclass(view_cls, APIView)

        # only process our own views
        if not view_cls.__module__.startswith("woo_publications."):
            return view_cls

        # XXX: this can probably be made more specific in case the permission classes
        # are conditional based on the action, but for now that doesn't apply (yet)
        has_audit_header_permissions = any(
            # a class is a subclass of itself
            isclass(perm_cls) and issubclass(perm_cls, AuditHeaderPermission)
            for perm_cls in view_cls.permission_classes
        )
        if not has_audit_header_permissions:
            return view_cls

        @extend_schema(parameters=ALL_AUDIT_PARAMETERS)
        class Fixed(view_cls):
            pass

        return Fixed
