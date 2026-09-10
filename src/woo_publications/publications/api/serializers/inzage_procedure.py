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
