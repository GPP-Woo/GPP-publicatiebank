from __future__ import annotations

from datetime import datetime
from functools import partial
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import InlineModelAdmin
from django.db import models, transaction
from django.http import HttpRequest
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _, ngettext

from furl import furl

from woo_publications.logging.service import AdminAuditLogMixin, get_logs_link
from woo_publications.metadata.models import Organisation
from woo_publications.typing import is_authenticated_request

from .constants import PublicationStatusOptions
from .formset import DocumentAuditLogInlineformset
from .models import Document, Publication, Topic
from .tasks import (
    index_document,
    index_publication,
    remove_document_from_index,
    remove_from_index_by_uuid,
    remove_publication_from_index,
)


# TODO: extend this func to work with `Topic`
@admin.action(
    description=_("Send the selected %(verbose_name_plural)s to the search index")
)
def sync_to_index(
    modeladmin: PublicationAdmin | DocumentAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication | Document],
):
    model = queryset.model
    filtered_qs = queryset.filter(publicatiestatus=PublicationStatusOptions.published)
    if model is Document:
        filtered_qs = filtered_qs.filter(
            publicatie__publicatiestatus=PublicationStatusOptions.published
        )

    num_objects = filtered_qs.count()

    if model not in [Publication, Document]:  # pragma: no cover
        raise ValueError("Unknown model: %r", model)

    for obj in filtered_qs.iterator():
        if model is Publication:
            transaction.on_commit(
                partial(index_publication.delay, publication_id=obj.pk)
            )
        elif model is Document:
            assert isinstance(obj, Document)
            document_url = obj.absolute_document_download_uri(request)
            transaction.on_commit(
                partial(
                    index_document.delay, document_id=obj.pk, download_url=document_url
                )
            )
        else:  # pragma: no cover
            assert False, "unreachable"

    modeladmin.message_user(
        request,
        ngettext(
            "{count} {verbose_name} scheduled for background processing.",
            "{count} {verbose_name_plural} scheduled for background processing.",
            num_objects,
        ).format(
            count=num_objects,
            verbose_name=model._meta.verbose_name,
            verbose_name_plural=model._meta.verbose_name_plural,
        ),
        messages.SUCCESS,
    )


# TODO: extend this func to work with `Topic`
@admin.action(
    description=_("Remove the selected %(verbose_name_plural)s from the search index")
)
def remove_from_index(
    modeladmin: PublicationAdmin | DocumentAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication | Document],
):
    model = queryset.model
    num_objects = queryset.count()

    if model is Publication:
        task_fn = remove_publication_from_index
        kwarg_name = "publication_id"
    elif model is Document:
        task_fn = remove_document_from_index
        kwarg_name = "document_id"
    else:  # pragma: no cover
        raise ValueError("Unsupported model: %r", model)

    for obj in queryset.iterator():
        transaction.on_commit(
            partial(task_fn.delay, force=True, **{kwarg_name: obj.pk})
        )

    modeladmin.message_user(
        request,
        ngettext(
            "{count} {verbose_name} scheduled for background processing.",
            "{count} {verbose_name_plural} scheduled for background processing.",
            num_objects,
        ).format(
            count=num_objects,
            verbose_name=model._meta.verbose_name,
            verbose_name_plural=model._meta.verbose_name_plural,
        ),
        messages.SUCCESS,
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
    autocomplete_fields = (
        "informatie_categorieen",
        "onderwerpen",
    )
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
    actions = [sync_to_index, remove_from_index]

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

    def get_formset_kwargs(
        self,
        request: HttpRequest,
        obj: Publication | None,
        inline: InlineModelAdmin[Any, Publication],
        prefix: str,
    ):
        kwargs = super().get_formset_kwargs(request, obj, inline, prefix)

        # add the request to the create formset instance so that we can generate absolute
        # URLs
        if isinstance(inline, DocumentInlineAdmin):
            kwargs["request"] = request

        return kwargs

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
        "uuid",
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
    actions = [sync_to_index, remove_from_index]

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
            download_url = obj.absolute_document_download_uri(request)
            transaction.on_commit(
                partial(
                    index_document.delay, document_id=obj.pk, download_url=download_url
                )
            )

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


class PublicationInline(admin.StackedInline):
    model = Publication.onderwerpen.through
    autocomplete_fields = ("publication",)
    extra = 0

    # TODO: allow altering of inlineformset
    def has_add_permission(self, request: HttpRequest, obj=None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=None):
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return False


@admin.register(Topic)
class TopicAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    list_display = (
        "officiele_titel",
        "publicatiestatus",
        "registratiedatum",
        "promoot",
        "uuid",
        "show_actions",
    )
    readonly_fields = (
        "uuid",
        "registratiedatum",
        "laatst_gewijzigd_datum",
    )
    search_fields = (
        "uuid",
        "officiele_titel",
    )
    list_filter = (
        "registratiedatum",
        "publicatiestatus",
        "promoot",
    )
    inlines = (PublicationInline,)
    date_hierarchy = "registratiedatum"
    # TODO: uncomment actions when we offer the data to GPP-zoeken
    # actions = [sync_to_index, remove_from_index]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.path == reverse("admin:autocomplete"):
            qs = qs.order_by("officiele_titel")
        return qs

    @admin.display(description=_("actions"))
    def show_actions(self, obj: Topic) -> str:
        actions = [
            get_logs_link(obj),
        ]
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )
