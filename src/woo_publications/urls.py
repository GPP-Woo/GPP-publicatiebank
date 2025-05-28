from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

handler500 = "maykin_common.views.server_error"
admin.site.enable_nav_sidebar = False
admin.site.site_header = _("WOO publications")
admin.site.site_title = _("WOO publications")
admin.site.index_title = _("WOO publications dashboard")

# URL routing

urlpatterns = [
    path("admin/", include("woo_publications.admin.urls")),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("api/", include("woo_publications.api.urls")),
    path("catalogi/api/v1/", include("woo_publications.contrib.documents_api.api")),
    # Simply show the index template.
    path("", TemplateView.as_view(template_name="index.html"), name="root"),
    path("auth/oidc/", include("mozilla_django_oidc.urls")),
]

# NOTE: The staticfiles_urlpatterns also discovers static files (ie. no need to run
# collectstatic). Both the static folder and the media folder are only served via
# Django if DEBUG = True.
urlpatterns += staticfiles_urlpatterns() + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)

if settings.DEBUG and apps.is_installed("debug_toolbar"):  # pragma: no cover
    import debug_toolbar  # pyright: ignore

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

if apps.is_installed("rosetta"):  # pragma: no cover
    urlpatterns = [path("admin/rosetta/", include("rosetta.urls"))] + urlpatterns
