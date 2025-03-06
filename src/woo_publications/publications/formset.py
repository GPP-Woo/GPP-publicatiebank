from functools import partial

from django.db import transaction

from woo_publications.logging.admin_tools import AuditLogInlineformset

from .constants import PublicationStatusOptions
from .tasks import index_document, remove_document_from_index


# TODO: send the download_url with the index_document task.
class DocumentAuditLogInlineformset(AuditLogInlineformset):
    def save_new(self, form, commit=True):
        document = super().save_new(form, commit)
        if document.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(index_document.delay, document_id=document.pk)
            )
        return document

    def save_existing(self, form, obj, commit=True):
        match obj.publicatiestatus:
            case PublicationStatusOptions.published:
                transaction.on_commit(partial(index_document.delay, document_id=obj.pk))
            case _:
                transaction.on_commit(
                    partial(remove_document_from_index.delay, document_id=obj.pk)
                )
        super().save_existing(form, obj, commit)

    def delete_existing(self, obj, commit=True):
        if obj.publicatiestatus == PublicationStatusOptions.published:
            transaction.on_commit(
                partial(remove_document_from_index.delay, document_id=obj.pk)
            )
        super().delete_existing(obj, commit)
