from functools import partial

from django.db import transaction

from woo_publications.logging.admin_tools import AuditLogInlineformset

from .tasks import index_document


class DocumentAuditLogInlineformset(AuditLogInlineformset):
    def save_new(self, form, commit=True):
        document = super().save_new(form, commit)
        transaction.on_commit(partial(index_document.delay, document_id=document.pk))
        return document

    def save_existing(self, form, obj, commit=True):
        transaction.on_commit(partial(index_document.delay, document_id=obj.pk))
        super().save_existing(form, obj, commit)
