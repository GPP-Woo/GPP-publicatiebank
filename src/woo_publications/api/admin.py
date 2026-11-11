from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from woo_publications.logging.admin_tools import AdminAuditLogMixin

from ..logging.logevent import audit_admin_read
from ..typing import is_authenticated_request
from .models import Application


@admin.register(Application)
class ApplicationAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = (
        "contact_person",
        "email",
        "phone_number",
        "created",
        "active",
    )
    exclude = (
        "token",
        "viewed_token_at",
    )
    ignore_logging_fields = ("token",)

    @admin.display(boolean=True, description=_("active"))
    def active(self, obj):
        if expire_date := obj.expire_date:
            return expire_date > timezone.localdate()

        return True

    def response_add(self, request, obj, post_url_continue=None):
        return redirect("admin:token_view", object_id=obj.pk)

    def render_change_form(self, request, context, *args, **kwargs):
        if not context.get("original"):
            context.update(
                {
                    "show_save_and_add_another": False,
                    "show_save_and_continue": False,
                    "show_save_as_new": False,
                }
            )

        return super().render_change_form(request, context, *args, **kwargs)

    def get_urls(self):
        default_urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/token/",
                self.admin_site.admin_view(self.token_view_endpoint),
                name="token_view",
            ),
        ]
        return custom_urls + default_urls

    @transaction.atomic
    def token_view_endpoint(self, request: HttpRequest, object_id: int) -> HttpResponse:
        assert is_authenticated_request(request)

        if not self.has_view_permission(request) or not self.has_add_permission(
            request
        ):
            raise PermissionDenied

        application = get_object_or_404(
            Application.objects.select_for_update(), pk=object_id
        )

        if application.viewed_token_at or application.token:
            raise Http404("Token already viewed")

        token = application.get_and_set_token()
        application.viewed_token_at = timezone.now()
        application.save(update_fields=["viewed_token_at", "token"])

        context = {
            **self.admin_site.each_context(request),
            "title": _("Applicatie-API-Key  Token:"),
            "opts": self.model._meta,
            "application": application,
            "token": token,
            "cl": {"opts": self.model._meta},
            "url_prefix": request.build_absolute_uri("/")[
                :-1
            ],  # strip off the trailing slash
        }

        audit_admin_read(content_object=application, django_user=request.user)

        return render(request, "admin/token.html", context)
