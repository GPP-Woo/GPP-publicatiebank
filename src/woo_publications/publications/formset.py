from functools import partial

from django.db import transaction
from django.forms import ModelForm
from django.http import HttpRequest

from woo_publications.accounts.models import OrganisationMember, User
from woo_publications.logging.admin_tools import AuditLogInlineformset

from .constants import PublicationStatusOptions
from .models import Document, Publication
from .tasks import remove_document_from_index


class DocumentInlineformset(AuditLogInlineformset[Document, Publication, ModelForm]):
    request: HttpRequest
    instance: Publication

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

    def save_new(self, form: ModelForm[Document], commit=True):
        # save it manually so that we have a guaranteed record in the database, allowing
        # us to call the state transitions later
        document = super().save_new(form, commit=False)
        document.save()

        # call the state transitions before the main save, otherwise the audit logs
        # record the wrong snapshot data
        match self.instance.publicatiestatus:
            case PublicationStatusOptions.concept:
                document.draft()
            case PublicationStatusOptions.published:
                document.publish(request=self.request)
            case _:  # pragma: no cover
                # you can't create new documents for revoked publications
                raise RuntimeError("Unreachable code")

        return super().save_new(form, commit)

    def delete_existing(self, obj, commit=True):
        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(remove_document_from_index.delay, document_id=obj.pk)
            )
        super().delete_existing(obj, commit)
