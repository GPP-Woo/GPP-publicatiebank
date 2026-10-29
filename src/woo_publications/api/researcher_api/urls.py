from django.urls import include, path
from django.views.generic import RedirectView

from drf_spectacular.views import SpectacularJSONAPIView, SpectacularRedocView
from rest_framework import routers

from .settings import custom_settings

app_name = "researcher"

router = routers.DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_format_suffixes = False


urlpatterns = [
    path(
        "docs/", RedirectView.as_view(pattern_name="researcher:schema-redoc-researcher")
    ),
    path(
        "v1/",
        include(
            [
                path(
                    "openapi.json",
                    SpectacularJSONAPIView.as_view(
                        schema=None,
                        urlconf="woo_publications.api.researcher_api.urls",
                        custom_settings=custom_settings,
                    ),
                    name="schema-json-researcher",
                ),
                path(
                    "docs/",
                    SpectacularRedocView.as_view(
                        url_name="researcher:schema-json-researcher"
                    ),
                    name="schema-redoc-researcher",
                ),
            ]
        ),
    ),
    path("v1/", include(router.urls)),
]
