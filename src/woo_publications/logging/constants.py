from django.db import models
from django.utils.translation import gettext_lazy as _

from woo_publications.logging.typing import ActingUser

SYSTEM_USER: ActingUser = {"identifier": "system", "display_name": "system"}


class Events(models.TextChoices):
    # generic events mapping to standard CRUD operations
    create = "create", _("Record created")
    read = "read", _("Record read")
    update = "update", _("Record updated")
    delete = "delete", _("Record deleted")
    # Specific events
    download = "download", _("Downloaded")
    delete_document = "delete_document", _("Document deleted")
