from django.conf import settings
from django.utils.translation import gettext_lazy as _

custom_settings = {
    "SCHEMA_PATH_PREFIX_INSERT": "/api",
    "TITLE": "GPP Publications - Researcher API",
    "DESCRIPTION": _("TODO"),
    "VERSION": settings.RESEARCHER_API_VERSION,
    "TAGS": [],
}
