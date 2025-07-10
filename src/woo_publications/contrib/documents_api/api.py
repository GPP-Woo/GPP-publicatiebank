"""
Implement a placeholder/mock "Catalogi API" endpoint for informatieobjecttype resource.

The real implementation will translation the
:class:`woo_publications.metadata.models.InformatieCategorie` into something that is
API standard compliant.
"""

from uuid import UUID

from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, views
from rest_framework.request import Request
from rest_framework.response import Response
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.metadata.models import InformationCategory

DUMMY_IC_UUID: UUID = UUID("0f06fded-7e08-437d-9fa2-021841a93842")
FIXED_DUMMY_IOT_DATA = {
    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.openbaar,
    "begin_geldigheid": "2024-09-01",
    "concept": False,
    "informatieobjectcategorie": "Wet Open Overheid",
    "besluittypen": [],
    "zaaktypen": [],
}


class CatalogiAPIDocumentTypeSerializer(serializers.Serializer):
    url = serializers.URLField(read_only=True)
    catalogus = serializers.URLField(
        help_text=(
            "URL-referentie naar de CATALOGUS waartoe dit INFORMATIEOBJECTTYPE behoort."
        ),
    )
    begin_geldigheid = serializers.DateField(
        help_text="De datum waarop het is ontstaan.",
    )
    informatieobjectcategorie = serializers.CharField(
        max_length=80,
        help_text=(
            "Typering van de aard van informatieobjecten van dit INFORMATIEOBJECTTYPE."
        ),
    )
    omschrijving = serializers.CharField(
        max_length=80,
        help_text=(
            "Omschrijving van de aard van informatieobjecten van dit "
            "INFORMATIEOBJECTTYPE."
        ),
    )
    vertrouwelijkheidaanduiding = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        help_text=(
            "Aanduiding van de mate waarin informatieobjecten van dit "
            "INFORMATIEOBJECTTYPE voor de openbaarheid bestemd zijn."
        ),
    )
    concept = serializers.BooleanField(
        read_only=True,
        help_text=(
            "Geeft aan of het object een concept betreft. Concepten zijn "
            "niet-definitieve versies en zouden niet gebruikt moeten worden buiten "
            "deze API."
        ),
    )
    besluittypen = serializers.ListField(
        child=serializers.URLField(),
        read_only=True,
        help_text="URL-referenties naar de BESLUITTYPEN",
    )
    zaaktypen = serializers.ListField(
        child=serializers.URLField(),
        read_only=True,
        help_text="URL-referenties naar de ZAAKTYPEN",
    )


@extend_schema(
    summary=_("Retrieve a document type"),
    tags=["Catalogi API"],
    responses={200: CatalogiAPIDocumentTypeSerializer},
)
class CatalogiAPIDocumentTypeView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def get(self, request: Request, uuid: UUID, *args, **kwargs):
        """
        Expose an information category as a Catalogi API `informatieobjecttype`.

        **NOTE**: this API endpoint is internal and used in the integration with the
        Documenten API. Publication components are not expected to interact with it.
        """
        if uuid == DUMMY_IC_UUID:
            information_category = InformationCategory(uuid=DUMMY_IC_UUID)
        else:
            information_category = get_object_or_404(InformationCategory, uuid=uuid)

        data = {
            "url": request.build_absolute_uri(request.path),
            "catalogus": request.build_absolute_uri(
                "/catalogi/api/v1/catalogussen/-fake-"
            ),
            **FIXED_DUMMY_IOT_DATA,
            # API spec has upper limit of 80 chars - our model is now capped to 80
            # chars but this could change in the future
            "omschrijving": information_category.naam[:80],
        }
        serializer = CatalogiAPIDocumentTypeSerializer(instance=data)
        return Response(
            serializer.data,
            headers={
                "API-Version": "1.3.1",
                "ETag": "-placeholder-",
            },
        )


urlpatterns = [
    path(
        "informatieobjecttypen/<uuid:uuid>",
        CatalogiAPIDocumentTypeView.as_view(),
        name="catalogi-informatieobjecttypen-detail",
    ),
]
