from django.urls import include, path
from django.views.generic import RedirectView

from rest_framework import routers

from woo_publications.accounts.api.viewsets import OrganisationUnitViewSet
from woo_publications.metadata.api.viewsets import (
    InformationCategoryViewSet,
    OrganisationViewSet,
    ThemeViewSet,
)
from woo_publications.publications.api.viewsets import (
    DocumentViewSet,
    InzageProcedureViewSet,
    PublicationViewSet,
    TopicViewSet,
)

app_name = "api"

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
        "v2/docs/",
        RedirectView.as_view(pattern_name="standard:schema-redoc-standard"),
    ),
    path(
        "v3/docs/",
        RedirectView.as_view(pattern_name="standard:schema-redoc-standard"),
    ),
    path("v2/", include(router.urls)),
    path("v3/", include(router.urls)),
]
