from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Literal

from django import forms
from django.db import transaction
from django.http import HttpRequest
from django.utils.choices import BaseChoiceIterator
from django.utils.translation import gettext_lazy as _

import structlog

from woo_publications.accounts.models import OrganisationMember
from woo_publications.typing import is_authenticated_request

from .constants import PublicationStatusOptions
from .models import Document, Publication
from .tasks import index_document, index_publication

logger = structlog.stdlib.get_logger(__name__)


class ChangeOwnerForm(forms.Form):
    eigenaar = forms.ModelChoiceField(
        label=_("Owner"),
        queryset=OrganisationMember.objects.order_by("naam"),
        required=False,
    )
    identifier = forms.CharField(
        label=_("Identifier"),
        help_text=_("The (primary) unique identifier."),
        max_length=255,
        required=False,
    )
    naam = forms.CharField(
        label=_("Name"),
        max_length=255,
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        assert isinstance(cleaned_data, dict)

        has_eigenaar = bool(cleaned_data.get("eigenaar"))
        has_identifier = bool(cleaned_data.get("identifier"))
        has_naam = bool(cleaned_data.get("naam"))

        match (has_eigenaar, has_identifier, has_naam):
            case (False, False, False):
                self.add_error(
                    None,
                    error=_(
                        "You need to provide a valid 'owner' or "
                        "'identifier' and 'name'."
                    ),
                )
            case (True, False, False):
                pass
            case (False, True, False):
                self.add_error("naam", error=_("This field is required."))
            case (False, False, True):
                self.add_error("identifier", error=_("This field is required."))

        return cleaned_data


class PublicationStatusForm[M: Publication | Document](forms.ModelForm[M]):
    request: HttpRequest
    initial_publication_status: PublicationStatusOptions | Literal[""]

    def __init__(self, *args, request: HttpRequest, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.initial_publication_status = self.instance.publicatiestatus

        publicatiestatus_field = self.fields.get("publicatiestatus")
        if self.instance and publicatiestatus_field is not None:
            assert isinstance(publicatiestatus_field, forms.ChoiceField)
            allowed_values: set[str] = {
                status.target.value
                for status in self.instance.get_available_publicatiestatus_transitions()
            }
            if selected_publicatiestatus := self.instance.publicatiestatus:
                allowed_values.add(selected_publicatiestatus)

            assert isinstance(publicatiestatus_field.choices, BaseChoiceIterator)
            publicatiestatus_field.choices = [
                choice
                for choice in publicatiestatus_field.choices
                if choice[0] in allowed_values
            ]


class PublicationAdminForm(PublicationStatusForm[Publication]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data.get("publicatiestatus") == PublicationStatusOptions.concept:
            for field in self.fields:
                # Ensure that officiele_titel remains required.
                if field != "officiele_titel":
                    self.fields[field].required = False

    def save(self, commit=True):
        assert is_authenticated_request(self.request)
        apply_retention_policy = False
        reindex_documents = False
        new_publication_status = self.cleaned_data.pop("publicatiestatus")
        # reset the publication status to the 'current' status - at this point the
        # instance has the newly selected status because of ModelForm._post_clean which
        # assigns the cleaned_data to the instance *before* the save is called.
        # Failing to reset this brings us to invalid state transitions.
        self.instance.publicatiestatus = self.initial_publication_status

        # prepare the callback to invoke after saving the publication to the database,
        # which requires the PK to be known to be able to dispatch celery tasks.
        post_save_callback: Callable[[], None] | None = None

        match (self.initial_publication_status, new_publication_status):
            # newly created concept
            case ("", PublicationStatusOptions.concept):
                post_save_callback = self.instance.draft
            # newly created published or existing concept being published
            case (
                "" | PublicationStatusOptions.concept,
                PublicationStatusOptions.published,
            ):
                post_save_callback = partial(
                    self.instance.publish, request=self.request, user=self.request.user
                )
                apply_retention_policy = True
            # revoke published
            case (PublicationStatusOptions.published, PublicationStatusOptions.revoked):
                post_save_callback = partial(
                    self.instance.revoke, user=self.request.user
                )
            case _:
                assert self.instance.pk is not None, (
                    "Codepath may not hit for new instances"
                )
                # ensure that the search index is updated - publish/revoke state
                # transitions call these tasks themselves
                transaction.on_commit(
                    partial(index_publication.delay, publication_id=self.instance.pk)
                )
                logger.debug(
                    "state_transition_skipped",
                    source_status=self.initial_publication_status,
                    target_status=new_publication_status,
                    model=Publication._meta.model_name,
                    pk=self.instance.pk,
                )
                if "informatie_categorieen" in self.changed_data:
                    apply_retention_policy = True
                # According ticket #309 the document data must re-index when
                # publication updates `publisher` or `informatie_categorieen`.
                if any(
                    match in self.changed_data
                    for match in ["publisher", "informatie_categorieen"]
                ):
                    reindex_documents = True

        publication = super().save(commit=commit)
        # cannot force the commit as True because of the AttributeError:
        # 'PublicationForm' object has no attribute 'save_m2m'.
        # So we manually save it after running the super
        if not publication.pk:
            publication.save()

        if post_save_callback is not None:
            post_save_callback()

        if apply_retention_policy:
            self.save_m2m()
            publication.apply_retention_policy()

        if reindex_documents:
            for document in self.instance.document_set.iterator():  # pyright: ignore[reportAttributeAccessIssue]
                transaction.on_commit(
                    partial(index_document.delay, document_id=document.pk)
                )

        if self.instance.pk and "publisher" in self.changed_data:
            publication.update_documents_rsin()

        return publication


class DocumentAdminForm(PublicationStatusForm[Document]):
    def save(self, commit=True):
        new_publication_status = self.instance.publicatie.publicatiestatus
        # ignore the form field unless it's set to revoke
        specified_new_publication_status = self.cleaned_data.pop(
            "publicatiestatus", None
        )
        if specified_new_publication_status == PublicationStatusOptions.revoked:
            new_publication_status = specified_new_publication_status

        # reset the document status to the 'current' status - at this point the
        # instance has the newly selected status because of ModelForm._post_clean which
        # assigns the cleaned_data to the instance *before* the save is called.
        # Failing to reset this brings us to invalid state transitions.
        self.instance.publicatiestatus = self.initial_publication_status

        # prepare the callback to invoke after saving the document to the database,
        # which requires the PK to be known to be able to dispatch celery tasks.
        post_save_callback: Callable[[], None] | None = None

        match (self.initial_publication_status, new_publication_status):
            # newly created concept
            case ("", PublicationStatusOptions.concept):
                post_save_callback = self.instance.draft
            # newly created published or existing concept being published
            case (
                "" | PublicationStatusOptions.concept,
                PublicationStatusOptions.published,
            ):
                post_save_callback = partial(
                    self.instance.publish, request=self.request
                )
            # revoke published
            case (PublicationStatusOptions.published, PublicationStatusOptions.revoked):
                post_save_callback = self.instance.revoke
            case _:
                assert self.instance.pk is not None, (
                    "Codepath may not hit for new instances"
                )
                # ensure that the search index is updated - publish/revoke state
                # transitions call these tasks themselves
                download_url = self.instance.absolute_document_download_uri(
                    self.request
                )
                transaction.on_commit(
                    partial(
                        index_document.delay,
                        document_id=self.instance.pk,
                        download_url=download_url,
                    )
                )
                logger.debug(
                    "state_transition_skipped",
                    source_status=self.initial_publication_status,
                    target_status=new_publication_status,
                    model=Document._meta.model_name,
                    pk=self.instance.pk,
                )

        document = super().save(commit=commit)
        # cannot force the commit as True because of the AttributeError:
        # 'DocumentForm' object has no attribute 'save_m2m'.
        # So we manually save it after running the super
        if not document.pk:
            document.save()

        if post_save_callback is not None:
            post_save_callback()

        return document
