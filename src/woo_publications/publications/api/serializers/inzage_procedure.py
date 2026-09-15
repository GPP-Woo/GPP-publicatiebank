from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from ...models import InzageProcedure, Publication


class InzageProcedureSerializer(serializers.ModelSerializer[InzageProcedure]):
    publicatie = serializers.SlugRelatedField(
        queryset=Publication.objects.only("uuid"),
        slug_field="uuid",
        help_text=_("The unique identifier of the publication."),
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


class NestedInzageProcedureSerializer(InzageProcedureSerializer):
    class Meta(InzageProcedureSerializer.Meta):
        # Keep all the fields except Publication.
        fields = [
            field
            for field in InzageProcedureSerializer.Meta.fields
            if field != "publicatie"
        ]
