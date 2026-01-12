from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse_lazy
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _

from hijack.contrib.admin import HijackUserAdminMixin

from woo_publications.logging.service import AdminAuditLogMixin, get_logs_link

from .forms import PreventPrivilegeEscalationMixin, UserChangeForm
from .models import OrganisationMember, OrganisationUnit, User
from .utils import validate_max_user_permissions


@admin.register(User)
class UserAdmin(AdminAuditLogMixin, HijackUserAdminMixin, _UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "show_actions",
    )
    hijack_success_url = reverse_lazy("root")
    form = UserChangeForm

    def get_form(self, request, obj=None, change=False, **kwargs):
        ModelForm = super().get_form(request, obj, change=change, **kwargs)
        assert issubclass(ModelForm, PreventPrivilegeEscalationMixin | self.add_form)
        # Set the current and target user on the ModelForm class so they are
        # available in the instantiated form. See the comment in the
        # UserChangeForm for more details.
        ModelForm._current_user = request.user  # pyright: ignore
        ModelForm._target_user = obj  # pyright: ignore
        return ModelForm

    def user_change_password(self, request, id, form_url=""):
        user: User = self.get_object(request, unquote(id))  # pyright: ignore
        assert isinstance(request.user, User)
        try:
            validate_max_user_permissions(request.user, user)
        except ValidationError as exc:
            raise PermissionDenied from exc

        return super().user_change_password(request, id, form_url)

    @admin.display(description=_("actions"))
    def show_actions(self, obj: User) -> str:
        actions = [
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )


@admin.register(OrganisationMember)
class OrganisationMemberAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = ("identifier", "naam")
    search_fields = ("identifier",)
    ordering = ("naam",)

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = super().get_readonly_fields(request, obj)
        if obj:
            read_only_fields = ("identifier",)

        return read_only_fields


@admin.register(OrganisationUnit)
class OrganisationUnitAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = ("identifier", "naam")
    search_fields = ("identifier",)
    ordering = ("naam",)

    def get_readonly_fields(self, request, obj=None):
        read_only_fields = super().get_readonly_fields(request, obj)
        if obj:
            read_only_fields = ("identifier",)

        return read_only_fields
