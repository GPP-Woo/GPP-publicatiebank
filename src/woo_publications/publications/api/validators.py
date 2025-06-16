from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.settings import api_settings

from ..constants import PublicationStatusOptions
from ..models import Document, DocumentIdentifier, Publication, PublicationIdentifier
from ..typing import Kenmerk


class PublicationStatusValidator:
    """
    Validate the (specified) publicatiestatus state transition.

    The :class:`Document` and :class:`Publication` models both have a publicatiestatus
    field for which the state transitions are limited with a finite state machine.
    """

    requires_context = True

    def __call__(self, value: PublicationStatusOptions, field: serializers.ChoiceField):
        serializer = field.parent
        assert isinstance(serializer, serializers.ModelSerializer)
        model_cls = serializer.Meta.model  # pyright: ignore[reportGeneralTypeIssues]
        assert model_cls in (Document, Publication), (
            "Validator applied to unexpected model/serializer."
        )

        instance = serializer.instance or model_cls()
        assert isinstance(instance, Document | Publication)
        current_state = instance.publicatiestatus

        # no state change -> nothing to validate, since no transitions will be called.
        if value == current_state:
            return value

        # given the current instance and its available state transitions, validate that
        # the requested publicatiestatus is allowed.
        allowed_target_statuses: set[PublicationStatusOptions] = {
            status.target
            for status in instance.get_available_publicatiestatus_transitions()
        }
        if value not in allowed_target_statuses:
            message = _(
                "Changing the state from '{current}' to '{value}' is not allowed."
            ).format(current=current_state, value=value)
            raise serializers.ValidationError(message, code="invalid_state")

        return value


# This mimics the default UniqueConstraint validator with the difference
# that it ignores the kenmerken of its parent. This ensures that when
# updating a Publication or Document the current data can used without
# it raising an error
class KenmerkenValidator:
    requires_context = True

    def __init__(self, parent_field_name):
        self.parent_field_name = parent_field_name
        super().__init__()

    def __call__(self, value: Kenmerk, field: serializers.ModelSerializer):
        model_cls = field.Meta.model  # pyright: ignore[reportGeneralTypeIssues]
        assert model_cls in (DocumentIdentifier, PublicationIdentifier), (
            "Validator applied to unexpected model/serializer."
        )

        assert self.parent_field_name in [
            field.name for field in model_cls._meta.fields
        ]

        assert isinstance(field.parent.parent, serializers.ModelSerializer)
        parent_instance = (
            field.parent.parent.instance or field.parent.parent.Meta.model()  # pyright: ignore[reportGeneralTypeIssues]
        )
        assert isinstance(parent_instance, Document | Publication)

        query = model_cls.objects

        if parent_instance.pk:
            query = query.exclude(**{self.parent_field_name: parent_instance})

        if query.filter(kenmerk=value["kenmerk"], bron=value["bron"]).exists():
            error_message = _(
                "The fields {field_names} must make a unique set."
            ).format(field_names=", ".join(value))

            raise serializers.ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [error_message]}
            )

        return value
