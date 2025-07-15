from typing import TypedDict

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.request import Request

from woo_publications.accounts.models import OrganisationMember
from woo_publications.api.drf_spectacular.headers import (
    AUDIT_USER_ID_PARAMETER,
    AUDIT_USER_REPRESENTATION_PARAMETER,
)


class OwnerData(TypedDict):
    naam: str
    identifier: str


def update_or_create_organisation_member(
    request: Request, details: OwnerData | None = None
):
    if details is None:
        details = {
            "identifier": request.headers[AUDIT_USER_ID_PARAMETER.name],
            "naam": request.headers[AUDIT_USER_REPRESENTATION_PARAMETER.name],
        }
    return OrganisationMember.objects.get_and_sync(**details)


class EigenaarSerializer(serializers.ModelSerializer[OrganisationMember]):
    weergave_naam = serializers.CharField(
        source="naam",
        help_text=_("The display name of the user."),
    )

    class Meta:  # pyright: ignore
        model = OrganisationMember
        fields = (
            "identifier",
            "weergave_naam",
        )
        # Removed the none basic validators which are getting in the way for
        # update_or_create
        extra_kwargs = {"identifier": {"validators": []}}

    def validate(self, attrs):
        has_naam = bool(attrs.get("naam"))
        has_identifier = bool(attrs.get("identifier"))

        # added custom validator to check if both are present or not in case
        if has_naam != has_identifier:
            raise serializers.ValidationError(
                _(
                    "The fields 'naam' and 'weergaveNaam' has to be both "
                    "present or excluded."
                )
            )

        return super().validate(attrs)
