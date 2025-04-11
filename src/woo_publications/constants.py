from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ArchiveNominationChoices(TextChoices):
    retain = "blijvend_bewaren", _("Retain")
    destroy = "vernietigen", _("Dispose")
