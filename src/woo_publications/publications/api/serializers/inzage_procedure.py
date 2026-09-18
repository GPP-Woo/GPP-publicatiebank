from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from woo_publications.api.fields import WorkDateField

from ...models import InzageProcedure, Publication


class InzageProcedureSerializer(serializers.ModelSerializer[InzageProcedure]):
    publicatie = serializers.SlugRelatedField(
        queryset=Publication.objects.only("uuid"),
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
    )
    datum_einde_inzagetermijn = WorkDateField(
        label=_("in effect until").capitalize(),
        help_text=_(
            "The date when the inspection period comes to an end."
            "If the end date falls on a saturday, sunday or holiday we automatically "
            "push the date back to the first available workday."
        ),
    )

    class Meta:  # pyright: ignore
        model = InzageProcedure
        fields = (
            "uuid",
            "publicatie",
            "url_bekendmaking",
            "toelichting",
            "beschikbaar_rechtsmiddel",
            "url_reactieformulier",
            "datum_begin_inzagetermijn",
            "datum_einde_inzagetermijn",
            "automatisch_intrekken",
        )
        extra_kwargs = {
            "uuid": {
                "read_only": True,
            },
        }

    def validate(self, attrs):
        # user submitted data -> database data -> None (will never happen
        # since it's a required field)
        start_field = "datum_begin_inzagetermijn"
        start_date = attrs.get(start_field, getattr(self.instance, start_field, None))
        end_field = "datum_einde_inzagetermijn"
        end_date = attrs.get(end_field, getattr(self.instance, end_field, None))

        assert start_date
        assert end_date

        if start_date > end_date:
            raise serializers.ValidationError(
                {
                    "datum_einde_inzagetermijn": _(
                        "The end date cannot happen before the start date."
                    )
                }
            )

        return attrs


class NestedInzageProcedureSerializer(InzageProcedureSerializer):
    class Meta(InzageProcedureSerializer.Meta):
        # Keep all the fields except Publication.
        fields = [
            field
            for field in InzageProcedureSerializer.Meta.fields
            if field != "publicatie"
        ]
