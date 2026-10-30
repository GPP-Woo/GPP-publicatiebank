from django.urls import include, path
from django.views.generic import RedirectView

from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
)
from rest_framework import routers

from woo_publications.accounts.api.viewsets import OrganisationUnitViewSet
from woo_publications.metadata.api.viewsets.application import (
    InformationCategoryViewSet,
    OrganisationViewSet,
    ThemeViewSet,
)
from woo_publications.publications.api.viewsets.application import (
    DocumentViewSet,
    InzageProcedureViewSet,
    PublicationViewSet,
    TopicViewSet,
)

from .settings import custom_settings

app_name = "standard"

router = routers.DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_format_suffixes = False

router.register("accounts/organisatie-eenheden", OrganisationUnitViewSet)
router.register("documenten", DocumentViewSet)
router.register("informatiecategorieen", InformationCategoryViewSet)
router.register("inzageprocedure", InzageProcedureViewSet)
router.register("organisaties", OrganisationViewSet)
router.register("publicaties", PublicationViewSet)
router.register("themas", ThemeViewSet)
router.register("onderwerpen", TopicViewSet)

urlpatterns = [
    path("docs/", RedirectView.as_view(pattern_name="standard:schema-redoc-standard")),
    path(
        "v3/",
        include(
            [
                path(
                    "",
                    SpectacularJSONAPIView.as_view(
                        schema=None,
                        urlconf="woo_publications.api.application_api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-json-standard",
                ),
                path(
                    "docs/",
                    SpectacularRedocView.as_view(
                        url_name="standard:schema-json-standard"
                    ),
                    name="schema-redoc-standard",
                ),
            ]
        ),
    ),
    # TODO remove in future release
    path("v2/", include(router.urls)),
    path("v3/", include(router.urls)),
]
