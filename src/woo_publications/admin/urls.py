from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from maykin_2fa import monkeypatch_admin
from maykin_2fa.urls import urlpatterns, webauthn_urlpatterns
from maykin_common.accounts.views import PasswordResetView
from mozilla_django_oidc_db.views import AdminLoginFailure

# Configure admin

monkeypatch_admin()

urlpatterns = [
    path(
        "password_reset/",
        PasswordResetView.as_view(),
        name="admin_password_reset",
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path("hijack/", include("hijack.urls")),
    # Use custom login views for the admin + support hardware tokens
    path("login/failure/", AdminLoginFailure.as_view(), name="admin-oidc-error"),
    path("", include((urlpatterns, "maykin_2fa"))),
    path("", include((webauthn_urlpatterns, "two_factor"))),
    path("", admin.site.urls),
]
