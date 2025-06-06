from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Value, When
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _

from ordered_model.admin import OrderedModelAdmin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from woo_publications.logging.service import AdminAuditLogMixin, get_logs_link

from .constants import InformationCategoryOrigins, OrganisationOrigins
from .models import InformationCategory, Organisation, Theme


@admin.register(InformationCategory)
class InformationCategoryAdmin(AdminAuditLogMixin, OrderedModelAdmin):
    list_display = (
        "naam",
        "identifier",
        "oorsprong",
        "archiefnominatie",
        "bewaartermijn",
        "show_actions",
        "move_up_down_links",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "naam",
                    "naam_meervoud",
                    "definitie",
                    "omschrijving",
                    "oorsprong",
                    "identifier",
                    "uuid",
                )
            },
        ),
        (
            _("Archiving"),
            {
                "fields": (
                    "bron_bewaartermijn",
                    "selectiecategorie",
                    "archiefnominatie",
                    "bewaartermijn",
                    "toelichting_bewaartermijn",
                )
            },
        ),
    )
    _value_list_readonly_fields = (
        "uuid",
        "identifier",
        "naam",
        "naam_meervoud",
        "definitie",
        "oorsprong",
    )
    readonly_fields = (
        "uuid",
        "identifier",
        "oorsprong",
    )
    search_fields = (
        "identifier",
        "naam",
    )
    list_filter = ("oorsprong",)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.oorsprong == InformationCategoryOrigins.value_list:
            return self._value_list_readonly_fields

        return super().get_readonly_fields(request, obj)

    def get_urls(self):
        default_urls = super().get_urls()
        custom_urls = [
            path(
                "api-resources/",
                self.admin_site.admin_view(self.list_api_endpoints),
                name="metadata_informationcategory_iotendpoints",
            ),
        ]
        return custom_urls + default_urls

    @admin.display(description=_("actions"))
    def show_actions(self, obj: InformationCategory) -> str:
        actions = [
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )

    def list_api_endpoints(self, request: HttpRequest) -> HttpResponse:
        if not self.has_view_permission(request):
            raise PermissionDenied

        qs = InformationCategory.objects.annotate(
            origin_order=Case(
                When(oorsprong=InformationCategoryOrigins.value_list, then=Value(0)),
                When(oorsprong=InformationCategoryOrigins.custom_entry, then=Value(1)),
                default=Value(10),
            )
        ).order_by("origin_order", "order")
        context = {
            **self.admin_site.each_context(request),
            "title": _("Information object type API resource URLs"),
            "has_add_permission": self.has_add_permission(request),
            "opts": self.model._meta,
            "information_categories": qs,
            "cl": {"opts": self.model._meta},
            "url_prefix": request.build_absolute_uri("/")[
                :-1
            ],  # strip off the trailing slash
        }
        return render(
            request, "metadata/admin_information_category_api_resources.html", context
        )


@admin.register(Theme)
class ThemeAdmin(AdminAuditLogMixin, TreeAdmin):
    list_display = ("naam", "identifier", "show_actions")
    search_fields = ("identifier", "naam")
    form = movenodeform_factory(Theme)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description=_("actions"))
    def show_actions(self, obj: Theme) -> str:
        actions = [
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )


@admin.register(Organisation)
class OrganisationAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = (
        "naam",
        "identifier",
        "oorsprong",
        "is_actief",
        "show_actions",
    )
    readonly_fields = (
        "uuid",
        "oorsprong",
    )
    search_fields = (
        "identifier",
        "naam",
    )
    list_filter = ("oorsprong", "is_actief")

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = super().get_readonly_fields(request, obj)

        if obj and obj.oorsprong != OrganisationOrigins.custom_entry:
            read_only_fields += ("naam",)

        return read_only_fields

    @admin.display(description=_("actions"))
    def show_actions(self, obj: Organisation) -> str:
        actions = [
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )
