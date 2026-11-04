from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from woo_publications.logging.admin_tools import AdminAuditLogMixin

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

    @admin.display(boolean=True, description=_("active"))
    def active(self, obj):
        if expire_date := obj.expire_date:
            return expire_date > timezone.now().date()

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

    def token_view_endpoint(self, request: HttpRequest, object_id: int) -> HttpResponse:
        if not self.has_view_permission(request):
            raise PermissionDenied

        application = get_object_or_404(Application, pk=object_id)

        if application.viewed_token_at:
            raise Http404("Token already viewed")

        application.viewed_token_at = timezone.now()
        application.save()

        context = {
            **self.admin_site.each_context(request),
            "title": _("Applicatie-API-Key  Token:"),
            "opts": self.model._meta,
            "application": application,
            "cl": {"opts": self.model._meta},
            "url_prefix": request.build_absolute_uri("/")[
                :-1
            ],  # strip off the trailing slash
        }
        return render(request, "admin/token.html", context)
