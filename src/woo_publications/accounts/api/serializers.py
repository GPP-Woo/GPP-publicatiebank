from rest_framework import serializers

from ..models import OrganisationUnit


class OrganisationUnitSerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        model = OrganisationUnit
        fields = ("identifier", "naam")
        extra_kwargs = {
            "identifier": {
                "read_only": True,
            }
        }
