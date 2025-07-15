from collections.abc import Sequence

from django.utils.translation import gettext_lazy as _

from furl import furl
from requests import RequestException
from rest_framework import serializers
from zgw_consumers.models import Service

from woo_publications.contrib.documents_api.client import get_client

from ..constants import PublicationStatusOptions
from ..models import Document, Publication
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


class SourceDocumentURLValidator:
    """
    Validate that a source document URL points to a document in a known Documenten API.

    1. We must know the API root (i.e. have a service definition), otherwise we risk
       SSRF.
    2. The URL must point to a detail endpoint in the Documents API and we must have
       read permissions to be able to download it.
    """

    def __call__(self, url: str):
        # check if we have a service configured for this URL. If we don't, we can't
        # retrieve this URL.
        service = Service.get_service(url)
        if service is None:
            raise serializers.ValidationError(
                _("The provided URL (domain and port) are not supported."),
                code="unknown_service",
            )

        # validate the URL structure against the shape described in the Documents API
        # 1.x standard.
        # By definition the service matched on the longest shared prefix, so we know
        # that the segments of api_root are the leading segments of the provided URL.
        parsed_url = furl(url)
        num_api_root_segments = len(
            [x for x in furl(service.api_root).path.segments if x != ""]
        )
        relative_segments = parsed_url.path.segments[num_api_root_segments:]
        match relative_segments:
            case ["enkelvoudiginformatieobjecten", str()]:
                with get_client(service) as client:
                    try:
                        client.retrieve_document(url=url)
                    except RequestException as exc:
                        status_code = getattr(exc.response, "status_code", None)
                        raise serializers.ValidationError(
                            _(
                                "Could not look up the referenced document. Got "
                                "status_code={status_code} response."
                            ).format(status_code=status_code or "unknown"),
                            code="does_not_exist",
                        ) from exc
            case _:
                raise serializers.ValidationError(
                    _(
                        "The URL structure does not match the detail endpoint of a "
                        "Documents API 1.x enkelvoudiginformatieobject resource."
                    ),
                    code="invalid",
                )


def validate_duplicated_kenmerken(value: Sequence[Kenmerk]) -> None:
    if not value:
        return

    # transforms the nested dicts into a set and checks if the length is the same as
    # the original passed data. If the length is different that means that there were
    # duplicated items present because sets can't contain duplicate items.
    if (unique_value := {tuple(identifier.items()) for identifier in value}) and len(
        unique_value
    ) != len(value):
        raise serializers.ValidationError(
            _("You cannot provide identical identifiers.")
        )
