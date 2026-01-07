from django.urls import include, path
from django.views.generic import RedirectView

from drf_spectacular.views import SpectacularJSONAPIView, SpectacularRedocView
from rest_framework import routers

from woo_publications.accounts.api.viewsets import OrganisationUnitViewSet
from woo_publications.metadata.api.viewsets import (
    InformationCategoryViewSet,
    OrganisationViewSet,
    ThemeViewSet,
)
from woo_publications.publications.api.viewsets import (
    DocumentViewSet,
    PublicationViewSet,
    TopicViewSet,
)

app_name = "api"

router = routers.DefaultRouter(trailing_slash=False, use_regex_path=False)
router.include_format_suffixes = False

router.register("accounts/organisatie-eenheden", OrganisationUnitViewSet)
router.register("documenten", DocumentViewSet)
router.register("informatiecategorieen", InformationCategoryViewSet)
router.register("organisaties", OrganisationViewSet)
router.register("publicaties", PublicationViewSet)
router.register("themas", ThemeViewSet)
router.register("onderwerpen", TopicViewSet)

urlpatterns = [
    path("docs/", RedirectView.as_view(pattern_name="api:api-docs")),
    path(
        "v2/",
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
    # TODO remove in future release
    path("v1/", include(router.urls)),
    path("v2/", include(router.urls)),
]
