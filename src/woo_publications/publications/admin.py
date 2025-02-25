from datetime import datetime
from functools import partial

from django import forms
from django.contrib import admin
from django.db import transaction
from django.http import HttpRequest
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _

from furl import furl

from woo_publications.logging.service import AdminAuditLogMixin, get_logs_link
from woo_publications.metadata.models import Organisation
from woo_publications.typing import is_authenticated_request

from .constants import PublicationStatusOptions
from .formset import DocumentAuditLogInlineformset
from .models import Document, Publication
from .tasks import (
    index_document,
    index_publication,
    remove_document_from_index,
    remove_from_index_by_uuid,
    remove_publication_from_index,
)


class DocumentInlineAdmin(admin.StackedInline):
    formset = DocumentAuditLogInlineformset
    model = Document
    readonly_fields = (
        "registratiedatum",
        "laatst_gewijzigd_datum",
    )
    extra = 0


@admin.register(Publication)
class PublicationAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = (
        "officiele_titel",
        "verkorte_titel",
        "publicatiestatus",
        "registratiedatum",
        "uuid",
        "show_actions",
    )
    autocomplete_fields = ("informatie_categorieen",)
    raw_id_fields = (
        "publisher",
        "verantwoordelijke",
        "opsteller",
    )
    readonly_fields = (
        "uuid",
        "registratiedatum",
        "laatst_gewijzigd_datum",
    )
    search_fields = (
        "uuid",
        "officiele_titel",
        "verkorte_titel",
    )
    list_filter = (
        "registratiedatum",
        "publicatiestatus",
    )
    date_hierarchy = "registratiedatum"
    inlines = (DocumentInlineAdmin,)

    def has_change_permission(self, request, obj=None):
        if obj and obj.publicatiestatus == PublicationStatusOptions.revoked:
            return False
        return super().has_change_permission(request, obj)

    def save_model(
        self, request: HttpRequest, obj: Publication, form: forms.Form, change: bool
    ):
        assert is_authenticated_request(request)

        new_status = obj.publicatiestatus
        original_status = form.initial.get("publicatiestatus")
        is_status_change = change and new_status != original_status
        is_published = new_status == PublicationStatusOptions.published
        is_revoked = new_status == PublicationStatusOptions.revoked

        if is_revoked and is_status_change:
            obj.revoke_own_published_documents(request.user)

        super().save_model(request, obj, form, change)

        if change and is_status_change and not is_published:
            # remove publication itself
            transaction.on_commit(
                partial(remove_publication_from_index.delay, publication_id=obj.pk)
            )

        if is_published:
            transaction.on_commit(
                partial(index_publication.delay, publication_id=obj.pk)
            )

    def delete_model(self, request: HttpRequest, obj: Publication):
        published_document_uuids = list(
            Document.objects.filter(
                publicatiestatus=PublicationStatusOptions.published,
                publicatie=obj,
            ).values_list("uuid", flat=True)
        )

        super().delete_model(request, obj)

        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Publication",
                    uuid=str(obj.uuid),
                )
            )
            for document_uuid in published_document_uuids:
                transaction.on_commit(
                    partial(
                        remove_from_index_by_uuid.delay,
                        model_name="Document",
                        uuid=str(document_uuid),
                    )
                )

    @admin.display(description=_("actions"))
    def show_actions(self, obj: Publication) -> str:
        actions = [
            (
                furl(reverse("admin:publications_document_changelist")).add(
                    {"publicatie__exact": obj.pk}
                ),
                _("Show documents"),
            ),
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )


@admin.register(Document)
class DocumentAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = (
        "officiele_titel",
        "verkorte_titel",
        "bestandsnaam",
        "publicatiestatus",
        "show_filesize",
        "identifier",
        "registratiedatum",
        "upload_complete",
        "show_actions",
    )
    fieldsets = [
        (
            None,
            {
                "fields": (
                    "publicatie",
                    "identifier",
                    "officiele_titel",
                    "verkorte_titel",
                    "omschrijving",
                    "creatiedatum",
                    "bestandsformaat",
                    "bestandsnaam",
                    "bestandsomvang",
                    "publicatiestatus",
                    "registratiedatum",
                    "laatst_gewijzigd_datum",
                    "uuid",
                )
            },
        ),
        (
            _("Document actions"),
            {
                "fields": (
                    "soort_handeling",
                    "at_time",
                    "was_assciated_with",
                )
            },
        ),
        (
            _("Documents API integration"),
            {
                "fields": (
                    "document_service",
                    "document_uuid",
                    "lock",
                    "upload_complete",
                )
            },
        ),
    ]
    readonly_fields = (
        "uuid",
        "registratiedatum",
        "laatst_gewijzigd_datum",
        "at_time",
        "was_assciated_with",
    )
    search_fields = (
        "identifier",
        "officiele_titel",
        "verkorte_titel",
        "bestandsnaam",
        "publicatie__uuid",
    )
    list_filter = (
        "registratiedatum",
        "creatiedatum",
        "publicatiestatus",
    )
    date_hierarchy = "registratiedatum"

    def save_model(
        self, request: HttpRequest, obj: Document, form: forms.Form, change: bool
    ):
        super().save_model(request, obj, form, change)

        new_status = obj.publicatiestatus
        is_published = new_status == PublicationStatusOptions.published

        if change:
            original_status = form.initial["publicatiestatus"]
            if new_status != original_status and not is_published:
                transaction.on_commit(
                    partial(remove_document_from_index.delay, document_id=obj.pk)
                )

        if is_published:
            transaction.on_commit(partial(index_document.delay, document_id=obj.pk))

    def delete_model(self, request: HttpRequest, obj: Document):
        super().delete_model(request, obj)

        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Document",
                    uuid=str(obj.uuid),
                )
            )

    @admin.display(description=_("file size"), ordering="bestandsomvang")
    def show_filesize(self, obj: Document) -> str:
        return filesizeformat(obj.bestandsomvang)

    @admin.display(description=_("actions"))
    def show_actions(self, obj: Document) -> str:
        actions = [
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )

    @admin.display(description=_("at time"))
    def at_time(self, obj: Document) -> datetime:
        return obj.registratiedatum

    @admin.display(description=_("was associated with"))
    def was_assciated_with(self, obj: Document) -> Organisation | None:
        return obj.publicatie.verantwoordelijke
