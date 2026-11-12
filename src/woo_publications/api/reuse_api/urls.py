from django.urls import include, path
from django.views.generic import RedirectView

from drf_spectacular.views import SpectacularJSONAPIView, SpectacularRedocView
from rest_framework import routers

from woo_publications.metadata.api.viewsets.reuse import (
    InformationCategoryViewSet,
    OrganisationViewSet,
    ThemeViewSet,
)
from woo_publications.publications.api.viewsets.reuse import (
    DocumentViewSet,
    PublicationViewSet,
    TopicViewSet,
)

from .settings import custom_settings

app_name = "reuse"

router = routers.DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_format_suffixes = False

router.register("documenten", DocumentViewSet)
router.register("informatiecategorieen", InformationCategoryViewSet)
router.register("organisaties", OrganisationViewSet)
router.register("publicaties", PublicationViewSet)
router.register("themas", ThemeViewSet)
router.register("onderwerpen", TopicViewSet)

urlpatterns = [
    path("docs/", RedirectView.as_view(pattern_name="reuse:schema-redoc-reuse")),
    path(
        "v1/",
        include(
            [
                path(
                    "openapi.json",
                    SpectacularJSONAPIView.as_view(
                        schema=None,
                        urlconf="woo_publications.api.reuse_api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-json-reuse",
                ),
                path(
                    "docs/",
                    SpectacularRedocView.as_view(url_name="reuse:schema-json-reuse"),
                    name="schema-redoc-reuse",
                ),
            ]
        ),
    ),
    path("v1/", include(router.urls)),
]
