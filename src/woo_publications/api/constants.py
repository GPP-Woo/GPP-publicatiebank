from django.db import models
from django.utils.translation import gettext_lazy as _


class PermissionOptions(models.TextChoices):
    read = "read", _("Read")
    write = "write", _("Write")


class ApiOptions(models.TextChoices):
    application = "application", _("Application")
    reuse = "reuse", _("Reuse")
