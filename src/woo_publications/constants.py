from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ArchiveNominationChoices(TextChoices):
    retain = "blijvend_bewaren", _("Retain")
    destroy = "vernietigen", _("Dispose")


class StrippableFileTypes(TextChoices):
    pdf = "pdf", _("PDF File")
    open_document = "open_document", _("Open Document")
    ms_office_file = "ms_office_files", _("Microsoft Office Files")
