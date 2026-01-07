from __future__ import annotations

from functools import partial
from uuid import UUID

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.utils import model_ngettext
from django.db import models, transaction
from django.http import HttpRequest
from django.template.defaultfilters import filesizeformat, truncatechars
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _, ngettext

from furl import furl

from woo_publications.accounts.models import OrganisationMember, User
from woo_publications.logging.logevent import (
    audit_admin_update,
)
from woo_publications.logging.serializing import serialize_instance
from woo_publications.logging.service import AdminAuditLogMixin, get_logs_link
from woo_publications.typing import is_authenticated_request
from woo_publications.utils.admin import PastAndFutureDateFieldFilter

from .constants import PublicationStatusOptions
from .forms import ChangeOwnerForm, DocumentAdminForm, PublicationAdminForm
from .models import (
    Document,
    DocumentIdentifier,
    Publication,
    PublicationIdentifier,
    Topic,
)
from .tasks import (
    index_document,
    index_publication,
    index_topic,
    remove_document_from_documents_api,
    remove_document_from_index,
    remove_from_index_by_uuid,
    remove_publication_from_index,
    remove_topic_from_index,
)


@admin.action(
    description=_("Change %(verbose_name_plural)s owner(s)"), permissions=["change"]
)
def change_owner(
    modeladmin: PublicationAdmin | DocumentAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication | Document],
):
    assert isinstance(request.user, User)
    model_name = str(model_ngettext(queryset))
    opts = modeladmin.model._meta
    form = ChangeOwnerForm(request.POST if request.POST.get("post") else None)

    changeable_objects = [
        format_html(
            '<a href="{}">{}</a>',
            reverse(
                f"admin:{opts.app_label}_{opts.model_name}_change",
                kwargs={"object_id": item.id},
            ),
            item.officiele_titel,
        )
        for item in queryset
    ]

    if (post := request.POST) and post.get("post"):
        if form.is_valid():
            owner = form.cleaned_data["eigenaar"]
            if not owner:
                owner = OrganisationMember.objects.create(
                    identifier=form.cleaned_data["identifier"],
                    naam=form.cleaned_data["naam"],
                )

            for obj in queryset:
                obj.eigenaar = owner
                obj.save()

                audit_admin_update(
                    content_object=obj,
                    object_data=serialize_instance(obj),
                    django_user=request.user,
                )

            modeladmin.message_user(
                request,
                _("Successfully changed %(count)d owner(s) of %(items)s.")
                % {
                    "count": queryset.count(),
                    "items": model_ngettext(modeladmin.opts, queryset.count()),
                },
                messages.SUCCESS,
            )

            modeladmin.model.objects.bulk_update(queryset, ["eigenaar"])
            return

    context = {
        **modeladmin.admin_site.each_context(request),
        "title": _("Change owner"),
        "objects_name": model_name,
        "queryset": queryset,
        "changeable_objects": changeable_objects,
        "opts": opts,
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        "media": modeladmin.media,
        "form": form,
    }

    request.current_app = modeladmin.admin_site.name

    # Display the confirmation page
    return TemplateResponse(
        request,
        "admin/change_owner.html",
        context,
    )


@admin.action(
    description=_("Send the selected %(verbose_name_plural)s to the search index")
)
def sync_to_index(
    modeladmin: PublicationAdmin | DocumentAdmin | TopicAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication | Document | Topic],
):
    model = queryset.model
    filtered_qs = queryset.filter(publicatiestatus=PublicationStatusOptions.published)
    if model is Document:
        filtered_qs = filtered_qs.filter(
            publicatie__publicatiestatus=PublicationStatusOptions.published
        )

    num_objects = filtered_qs.count()

    if model not in [Publication, Document, Topic]:  # pragma: no cover
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
        elif model is Topic:
            transaction.on_commit(partial(index_topic.delay, topic_id=obj.pk))
        else:  # pragma: no cover
            raise AssertionError("unreachable")

    modeladmin.message_user(
        request,
        ngettext(
            "{count} {verbose_name} object scheduled for background processing.",
            "{count} {verbose_name} objects scheduled for background processing.",
            num_objects,
        ).format(
            count=num_objects,
            verbose_name=model._meta.verbose_name,
        ),
        messages.SUCCESS,
    )


@admin.action(
    description=_("Remove the selected %(verbose_name_plural)s from the search index")
)
def remove_from_index(
    modeladmin: PublicationAdmin | DocumentAdmin | TopicAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication | Document | Topic],
):
    model = queryset.model
    num_objects = queryset.count()

    if model is Publication:
        task_fn = remove_publication_from_index
        kwarg_name = "publication_id"
    elif model is Document:
        task_fn = remove_document_from_index
        kwarg_name = "document_id"
    elif model is Topic:
        task_fn = remove_topic_from_index
        kwarg_name = "topic_id"
    else:  # pragma: no cover
        raise ValueError("Unsupported model: %r", model)

    for obj in queryset.iterator():
        transaction.on_commit(
            partial(task_fn.delay, force=True, **{kwarg_name: obj.pk})
        )

    modeladmin.message_user(
        request,
        ngettext(
            "{count} {verbose_name} object scheduled for background processing.",
            "{count} {verbose_name} objects scheduled for background processing.",
            num_objects,
        ).format(
            count=num_objects,
            verbose_name=model._meta.verbose_name,
        ),
        messages.SUCCESS,
    )


@admin.action(
    description=_(
        "Reassess the retention policy of the selected %(verbose_name_plural)s."
    )
)
def reassess_retention_policy(
    modeladmin: PublicationAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication],
):
    for obj in queryset.iterator():
        obj.apply_retention_policy()

    modeladmin.message_user(
        request,
        ngettext(
            "Applied the reassessed retention policy to {count} {verbose_name} object.",
            "Applied the reassessed retention policy to {count} {verbose_name} "
            "objects.",
            queryset.count(),
        ).format(
            count=queryset.count(),
            verbose_name=modeladmin.model._meta.verbose_name,
        ),
        messages.SUCCESS,
    )


@admin.action(description=_("revoke the selected %(verbose_name_plural)s"))
def revoke(
    modeladmin: PublicationAdmin | DocumentAdmin | TopicAdmin,
    request: HttpRequest,
    queryset: models.QuerySet[Publication | Document | Topic],
):
    assert is_authenticated_request(request)
    queryset = queryset.exclude(publicatiestatus=PublicationStatusOptions.revoked)

    model = queryset.model
    num_objects = queryset.count()

    if model is Publication:
        task_fn = remove_publication_from_index
        kwarg_name = "publication_id"
    elif model is Document:
        task_fn = remove_document_from_index
        kwarg_name = "document_id"
    elif model is Topic:
        task_fn = remove_topic_from_index
        kwarg_name = "topic_id"
    else:  # pragma: no cover
        raise ValueError("Unsupported model: %r", model)

    for obj in queryset.iterator():
        if model in (Document, Publication):
            obj.ingetrokken_op = timezone.now()  # pyright: ignore[reportAttributeAccessIssue]

        obj.publicatiestatus = PublicationStatusOptions.revoked
        obj.save()

        audit_admin_update(
            content_object=obj,
            object_data=serialize_instance(obj),
            django_user=request.user,
        )

        transaction.on_commit(
            partial(task_fn.delay, force=True, **{kwarg_name: obj.pk})
        )

        if model is Publication:
            assert isinstance(obj, Publication)
            obj.revoke_own_documents(request.user)

    modeladmin.message_user(
        request,
        ngettext(
            "{count} {verbose_name} object revoked.",
            "{count} {verbose_name} objects revoked.",
            num_objects,
        ).format(
            count=num_objects,
            verbose_name=model._meta.verbose_name,
        ),
        messages.SUCCESS,
    )


class DocumentInlineAdmin(admin.TabularInline[Document, Publication]):
    model = Document
    fk_name = "publicatie"  # necessary for the template override
    template = "admin/publications/publication/document_inline.html"
    fields = (
        "truncated_title",
        "status",
        "registratiedatum",
        "laatst_gewijzigd_datum",
        "show_actions",
    )
    readonly_fields = fields
    can_delete = False

    @admin.display(description=_("official title"))
    def truncated_title(self, obj: Document) -> str:
        title = truncatechars(obj.officiele_titel, 40)
        return format_html(
            '<a href="{path}">{title}</a>',
            path=reverse("admin:publications_document_change", args=(obj.pk,)),
            title=title,
        )

    @admin.display(description=_("status"))
    def status(self, obj: Document) -> str:
        return obj.get_publicatiestatus_display()

    @admin.display(description=_("actions"))
    def show_actions(self, obj: Document) -> str:
        actions = [
            (
                reverse("admin:publications_document_delete", args=(obj.pk,)),
                _("Delete"),
            ),
        ]
        return format_html_join(
            " | ",
            '<a href="{}" target="_blank">{}</a>',
            actions,
        )

    def has_add_permission(self, request: HttpRequest, obj: Publication | None) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: Publication | None = None
    ) -> bool:
        return False


class PublicationIdentifierInlineAdmin(admin.TabularInline):
    model = PublicationIdentifier
    extra = 0


@admin.register(Publication)
class PublicationAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    form = PublicationAdminForm
    list_display = (
        "officiele_titel",
        "verkorte_titel",
        "publicatiestatus",
        "registratiedatum",
        "archiefnominatie",
        "archiefactiedatum",
        "uuid",
        "show_actions",
    )
    fieldsets = (
        (
            _("Description"),
            {
                "fields": (
                    "informatie_categorieen",
                    "onderwerpen",
                    "officiele_titel",
                    "verkorte_titel",
                    "omschrijving",
                    "datum_begin_geldigheid",
                    "datum_einde_geldigheid",
                    "publicatiestatus",
                    "uuid",
                )
            },
        ),
        (
            _("Actions"),
            {
                "fields": (
                    "registratiedatum",
                    "gepubliceerd_op",
                    "ingetrokken_op",
                    "laatst_gewijzigd_datum",
                )
            },
        ),
        (
            _("Actors"),
            {
                "fields": (
                    "publisher",
                    "verantwoordelijke",
                    "opsteller",
                    "eigenaar",
                    "eigenaar_groep",
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
                    "archiefactiedatum",
                    "toelichting_bewaartermijn",
                )
            },
        ),
    )
    autocomplete_fields = (
        "informatie_categorieen",
        "onderwerpen",
        "eigenaar",
        "eigenaar_groep",
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
        "gepubliceerd_op",
        "ingetrokken_op",
    )
    search_fields = (
        "uuid",
        "officiele_titel",
        "verkorte_titel",
        "eigenaar__identifier",
        "eigenaar_groep__identifier",
    )
    list_filter = (
        "registratiedatum",
        "publicatiestatus",
        "archiefnominatie",
        ("archiefactiedatum", PastAndFutureDateFieldFilter),
    )
    date_hierarchy = "registratiedatum"
    inlines = (
        PublicationIdentifierInlineAdmin,
        DocumentInlineAdmin,
    )
    actions = [
        sync_to_index,
        remove_from_index,
        reassess_retention_policy,
        revoke,
        change_owner,
    ]

    def has_change_permission(self, request, obj=None):
        if obj and obj.publicatiestatus == PublicationStatusOptions.revoked:
            return False
        return super().has_change_permission(request, obj)

    def get_changeform_initial_data(self, request: HttpRequest):
        assert isinstance(request.user, User)
        initial_data: dict = super().get_changeform_initial_data(request)
        owner = OrganisationMember.objects.get_and_sync(
            identifier=str(request.user.pk),
            naam=request.user.get_full_name() or request.user.username,
        )
        initial_data["eigenaar"] = owner
        return initial_data

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

    def delete_queryset(
        self, request: HttpRequest, queryset: models.QuerySet[Publication]
    ):
        publication_document_deletion_mapping: dict[UUID, list[UUID]] = {}
        for publication in queryset:
            publication_document_deletion_mapping[publication.uuid] = list(
                Document.objects.filter(
                    publicatiestatus=PublicationStatusOptions.published,
                    publicatie=publication,
                ).values_list("uuid", flat=True)
            )

        super().delete_queryset(request, queryset)

        for (
            publication_uuid,
            document_uuids,
        ) in publication_document_deletion_mapping.items():
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Publication",
                    uuid=str(publication_uuid),
                    force=True,
                )
            )
            for document_uuid in document_uuids:
                transaction.on_commit(
                    partial(
                        remove_from_index_by_uuid.delay,
                        model_name="Document",
                        uuid=str(document_uuid),
                        force=True,
                    )
                )

    def get_form(self, request: HttpRequest, obj=None, change=False, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        form = super().get_form(request, obj, change, **kwargs)
        return partial(form, request=request)  # pyright: ignore[reportCallIssue]

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
        if gpp_app_url := obj.gpp_app_url:
            actions.append((gpp_app_url, _("Open in app")))
        if gpp_burgerportaal_url := obj.gpp_burgerportaal_url:
            actions.append((gpp_burgerportaal_url, _("Open in burgerportaal")))
        return format_html_join(
            " | ",
            '<a href="{}">{}</a>',
            actions,
        )


class DocumentIdentifierInlineAdmin(admin.TabularInline):
    model = DocumentIdentifier
    extra = 0


@admin.register(Document)
class DocumentAdmin(AdminAuditLogMixin, admin.ModelAdmin):
    form = DocumentAdminForm
    list_display = (
        "officiele_titel",
        "verkorte_titel",
        "bestandsnaam",
        "publicatiestatus",
        "show_filesize",
        "registratiedatum",
        "upload_complete",
        "show_actions",
    )
    fieldsets = [
        (
            _("Description"),
            {
                "fields": (
                    "publicatie",
                    "officiele_titel",
                    "verkorte_titel",
                    "omschrijving",
                    "publicatiestatus",
                    "uuid",
                )
            },
        ),
        (
            _("Actions"),
            {
                "fields": (
                    "creatiedatum",
                    "ontvangstdatum",
                    "datum_ondertekend",
                    "registratiedatum",
                    "gepubliceerd_op",
                    "ingetrokken_op",
                    "laatst_gewijzigd_datum",
                )
            },
        ),
        (
            _("Actors"),
            {
                "fields": ("eigenaar",),
            },
        ),
        (
            _("File"),
            {
                "fields": (
                    "source_url",
                    "bestandsnaam",
                    "bestandsformaat",
                    "bestandsomvang",
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
        (
            _("Deprecated fields"),
            {
                "classes": ["collapse"],
                "fields": ("identifier",),
            },
        ),
    ]
    readonly_fields = (
        "uuid",
        "registratiedatum",
        "laatst_gewijzigd_datum",
        "gepubliceerd_op",
        "ingetrokken_op",
        "source_url",
    )
    search_fields = (
        "uuid",
        "officiele_titel",
        "verkorte_titel",
        "bestandsnaam",
        "publicatie__uuid",
        "eigenaar__identifier",
    )
    list_filter = (
        "registratiedatum",
        "creatiedatum",
        "publicatiestatus",
    )
    inlines = [
        DocumentIdentifierInlineAdmin,
    ]
    autocomplete_fields = ("eigenaar",)
    date_hierarchy = "registratiedatum"
    actions = [sync_to_index, remove_from_index, revoke, change_owner]

    def get_changeform_initial_data(self, request: HttpRequest):
        assert isinstance(request.user, User)
        initial_data: dict = super().get_changeform_initial_data(request)
        owner = OrganisationMember.objects.get_and_sync(
            identifier=str(request.user.pk),
            naam=request.user.get_full_name() or request.user.username,
        )
        initial_data["eigenaar"] = owner
        return initial_data

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj is None:
            readonly_fields += ("publicatiestatus",)
        else:
            readonly_fields += ("publicatie",)

        return readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj and obj.publicatiestatus == PublicationStatusOptions.revoked:
            return False
        return super().has_change_permission(request, obj)

    def get_form(self, request: HttpRequest, obj=None, change=False, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        form = super().get_form(request, obj, change, **kwargs)
        return partial(form, request=request)  # pyright: ignore[reportCallIssue]

    def delete_model(self, request: HttpRequest, obj: Document):
        assert is_authenticated_request(request)
        doc_id = obj.pk
        super().delete_model(request, obj)

        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Document",
                    uuid=str(obj.uuid),
                )
            )

        if obj.document_service and obj.document_uuid:
            transaction.on_commit(
                partial(
                    remove_document_from_documents_api.delay,
                    document_id=doc_id,
                    user_id=request.user.pk,
                    service_uuid=obj.document_service.uuid,
                    document_uuid=obj.document_uuid,
                )
            )

    def delete_queryset(
        self, request: HttpRequest, queryset: models.QuerySet[Document]
    ):
        assert is_authenticated_request(request)
        queryset = queryset.select_related("document_service")
        # evaluate and cache the queryset *before* the actual delete so that we can
        # dispatch cleanup tasks after the delete
        _objs_to_delete: list[Document] = list(queryset)

        super().delete_queryset(request, queryset)

        for document in _objs_to_delete:
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Document",
                    uuid=str(document.uuid),
                    force=True,
                )
            )
            if not document.document_service or not document.document_uuid:
                continue

            transaction.on_commit(
                partial(
                    remove_document_from_documents_api.delay,
                    document_id=document.id,
                    user_id=request.user.pk,
                    service_uuid=document.document_service.uuid,
                    document_uuid=document.document_uuid,
                )
            )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "publicatie":
            db = kwargs.get("using")
            default_qs = self.get_field_queryset(db, db_field, request)
            # get_field_queryset relies on two things:
            # - to have a registered admin panel
            # - for the admin panel to have the ordering param set or
            #   to have a valid db instance to retrieve the ordering
            #   from the model ordering
            # because the db instance of formfield_for_foreignkey can be None,
            # and we haven't defined a default ordering on in the publication admin,
            # means that we need to define a fallback scenario otherwise we won't
            # have a queryset to exclude the revoked publication from.
            if not default_qs:  # pragma: no cover
                default_qs = Publication.objects

            kwargs["queryset"] = default_qs.exclude(
                publicatiestatus=PublicationStatusOptions.revoked
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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


class PublicationInline(admin.StackedInline):
    model = Publication.onderwerpen.through
    verbose_name = _("Publication")
    verbose_name_plural = _("Publications")
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
    fieldsets = [
        (
            _("Description"),
            {
                "fields": (
                    "afbeelding",
                    "officiele_titel",
                    "omschrijving",
                    "publicatiestatus",
                    "promoot",
                    "uuid",
                )
            },
        ),
        (
            _("Actions"),
            {
                "fields": ("registratiedatum", "laatst_gewijzigd_datum"),
            },
        ),
    ]
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
        "publication__uuid",
        "officiele_titel",
    )
    list_filter = (
        "registratiedatum",
        "publicatiestatus",
        "promoot",
    )
    inlines = (PublicationInline,)
    date_hierarchy = "registratiedatum"
    actions = [sync_to_index, remove_from_index, revoke]

    def save_model(
        self, request: HttpRequest, obj: Topic, form: forms.Form, change: bool
    ):
        super().save_model(request, obj, form, change)

        new_status = obj.publicatiestatus
        is_published = new_status == PublicationStatusOptions.published

        if change:
            original_status = form.initial["publicatiestatus"]
            if new_status != original_status and not is_published:
                transaction.on_commit(
                    partial(remove_topic_from_index.delay, topic_id=obj.pk)
                )

        if is_published:
            transaction.on_commit(
                partial(
                    index_topic.delay,
                    topic_id=obj.pk,
                )
            )

    def delete_model(self, request: HttpRequest, obj: Document):
        super().delete_model(request, obj)

        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Topic",
                    uuid=str(obj.uuid),
                )
            )

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.path == reverse("admin:autocomplete"):
            qs = qs.order_by("officiele_titel")
        return qs

    def delete_queryset(self, request: HttpRequest, queryset: models.QuerySet[Topic]):
        topic_uuids: list[UUID] = [topic.uuid for topic in queryset]

        super().delete_queryset(request, queryset)

        for topic_uuid in topic_uuids:
            transaction.on_commit(
                partial(
                    remove_from_index_by_uuid.delay,
                    model_name="Topic",
                    uuid=str(topic_uuid),
                    force=True,
                )
            )

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
