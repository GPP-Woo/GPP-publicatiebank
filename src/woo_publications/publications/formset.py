from functools import partial

from django.db import transaction
from django.http import HttpRequest

from woo_publications.logging.admin_tools import AuditLogInlineformset

from .constants import PublicationStatusOptions
from .models import Document
from .tasks import index_document, remove_document_from_index
from .utils import absolute_document_download_uri


class DocumentAuditLogInlineformset(AuditLogInlineformset):
    request: HttpRequest

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def save_new(self, form, commit=True):
        document = super().save_new(form, commit)
        if document.publicatiestatus == PublicationStatusOptions.published:
            download_url = absolute_document_download_uri(
                self.request, document_uuid=document.uuid
            )
            transaction.on_commit(
                partial(
                    index_document.delay,
                    document_id=document.pk,
                    download_url=download_url,
                )
            )
        return document

    def save_existing(self, form, obj: Document, commit=True):
        match obj.publicatiestatus:
            case PublicationStatusOptions.published:
                download_url = absolute_document_download_uri(
                    self.request, document_uuid=obj.uuid
                )
                transaction.on_commit(
                    partial(
                        index_document.delay,
                        document_id=obj.pk,
                        download_url=download_url,
                    )
                )
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
