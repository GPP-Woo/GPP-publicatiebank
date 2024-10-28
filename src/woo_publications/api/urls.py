from django.urls import include, path
from django.views.generic import RedirectView

from drf_spectacular.views import SpectacularJSONAPIView, SpectacularRedocView
from rest_framework import routers

from woo_publications.metadata.api.viewsets import (
    InformationCategoryViewSet,
    OrganisationViewSet,
    ThemeViewSet,
)
from woo_publications.publications.api.viewsets import PublicationViewSet

app_name = "api"

router = routers.DefaultRouter(trailing_slash=False)

router.register("informatiecategorieen", InformationCategoryViewSet)
router.register("organisaties", OrganisationViewSet)
router.register("publicaties", PublicationViewSet)
router.register("themas", ThemeViewSet)

urlpatterns = [
    path("docs/", RedirectView.as_view(pattern_name="api:api-docs")),
    path(
        "v1/",
        include(
            [
                path(
                    "",
                    SpectacularJSONAPIView.as_view(schema=None),
                    name="api-schema-json",
                ),
                path(
                    "docs/",
                    SpectacularRedocView.as_view(url_name="api:api-schema-json"),
                    name="api-docs",
                ),
            ]
        ),
    ),
    path("v1/", include(router.urls)),
]
