from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from ..constants import PublicationStatusOptions
from ..models import Document, Publication


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
