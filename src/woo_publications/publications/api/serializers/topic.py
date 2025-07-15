from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from ...models import Publication, Topic


class TopicSerializer(serializers.ModelSerializer[Topic]):
    publicaties = serializers.SlugRelatedField(
        queryset=Publication.objects.all(),
        slug_field="uuid",
        help_text=_("The publication attached to this topic."),
        many=True,
        source="publication_set",
    )

    class Meta:  # pyright: ignore
        model = Topic
        fields = (
            "uuid",
            "afbeelding",
            "publicaties",
            "officiele_titel",
            "omschrijving",
            "publicatiestatus",
            "promoot",
            "registratiedatum",
            "laatst_gewijzigd_datum",
        )
