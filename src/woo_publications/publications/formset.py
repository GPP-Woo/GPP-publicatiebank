from functools import partial

from django.db import transaction
from django.http import HttpRequest

from woo_publications.accounts.models import OrganisationMember, User
from woo_publications.logging.admin_tools import AuditLogInlineformset

from .constants import PublicationStatusOptions
from .models import Publication
from .tasks import remove_document_from_index


class DocumentAuditLogInlineformset(AuditLogInlineformset):
    request: HttpRequest

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.initial_publicatiestatus = self.instance.publicatiestatus

    @property
    def empty_form(self):
        user = self.request.user
        assert isinstance(user, User)
        form = super().empty_form
        form.fields["eigenaar"].initial = OrganisationMember.objects.get_and_sync(
            identifier=user.pk, naam=user.get_full_name() or user.username
        )
        return form

    def save_new(self, form, commit=True):
        assert isinstance(self.instance, Publication)
        # set the publicatiestatus from the form instance to its parent.
        publicatie_status = form.instance.publicatiestatus = (
            self.instance.publicatiestatus
        )

        document = super().save_new(form, commit)

        if publicatie_status == PublicationStatusOptions.published:
            self.instance.publicatiestatus = self.initial_publicatiestatus
            document.publish(self.request)
            document.refresh_from_db()

        return document

    def delete_existing(self, obj, commit=True):
        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(remove_document_from_index.delay, document_id=obj.pk)
            )
        super().delete_existing(obj, commit)
