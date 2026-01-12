from typing import TypedDict

from django.core.validators import validate_slug
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.request import Request

from woo_publications.accounts.models import OrganisationMember, OrganisationUnit
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

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
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
                    "The fields 'naam' and 'weergaveNaam' have to be both "
                    "present or excluded."
                )
            )

        return super().validate(attrs)


class OwnerGroupData(TypedDict):
    naam: str
    identifier: str


def update_or_create_organisation_unit(details: OwnerGroupData):
    return OrganisationUnit.objects.get_and_sync(**details)


class EigenaarGroepSerializer(serializers.ModelSerializer[OrganisationUnit]):
    weergave_naam = serializers.CharField(
        source="naam",
        help_text=_("The display name of the organisation unit."),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = OrganisationUnit
        fields = (
            "identifier",
            "weergave_naam",
        )
        # Removed the default (uniqueness) validators which are getting in the way for
        # update_or_create
        extra_kwargs = {
            "identifier": {
                "validators": [validate_slug],
                "help_text": _(
                    "The system identifier that uniquely identifies the organisation "
                    "unit performing the action. Only letters, numbers, underscores or "
                    "hyphens are allowed."
                ),
            },
        }

    def validate(self, attrs):
        has_naam = bool(attrs.get("naam"))
        has_identifier = bool(attrs.get("identifier"))

        # added custom validator to check if both are present or not in case
        if has_naam != has_identifier:
            raise serializers.ValidationError(
                _(
                    "The fields 'naam' and 'weergaveNaam' have to be both "
                    "present or excluded."
                )
            )

        return super().validate(attrs)
