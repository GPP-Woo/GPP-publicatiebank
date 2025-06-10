from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework_recursive.fields import RecursiveField

from ..constants import OrganisationOrigins
from ..models import InformationCategory, Organisation, Theme


class InformationCategorySerializer(serializers.ModelSerializer):
    class Meta:  # pyright: ignore
        model = InformationCategory
        fields = (
            "uuid",
            "identifier",
            "naam",
            "naam_meervoud",
            "definitie",
            "omschrijving",
            "oorsprong",
            "order",
        )
        extra_kwargs = {
            "order": {
                "help_text": _(
                    "Controls the (default) ordering of categories in result lists."
                )
            },
        }


class OrganisationSerializer(serializers.ModelSerializer):
    instance: Organisation | None

    class Meta:  # pyright: ignore
        model = Organisation
        fields = ("uuid", "identifier", "naam", "oorsprong", "is_actief")
        read_only_fields = (
            "uuid",
            "identifier",
            "oorsprong",
        )
        extra_kwargs = {
            "naam": {
                "required": False,
                "help_text": _(
                    "The name of the organisation (can only be modified when "
                    "`oorsprong` is `{custom_entry}`)."
                ).format(custom_entry=OrganisationOrigins.custom_entry),
            },
            "is_actief": {
                "required": False,
            },
        }

    def validate(self, attrs):
        if (
            (instance := self.instance)
            and instance.oorsprong != OrganisationOrigins.custom_entry
            and attrs.get("naam")
        ):
            raise serializers.ValidationError(
                {
                    "naam": _(
                        "You cannot modify the name of organisations populated from a "
                        "value list."
                    )
                }
            )

        return super().validate(attrs)


class ThemeSerializer(serializers.ModelSerializer):
    sub_themes = serializers.ListField(
        source="get_children",
        child=RecursiveField(),
        help_text=_("The nested themes attached to this current theme."),
    )

    class Meta:  # pyright: ignore
        model = Theme
        fields = (
            "uuid",
            "identifier",
            "naam",
            "sub_themes",
        )
