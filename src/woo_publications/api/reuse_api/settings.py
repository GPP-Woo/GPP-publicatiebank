from django.conf import settings
from django.utils.translation import gettext_lazy as _

custom_settings = {
    "TITLE": "GPP Publications - Reuse API",
    "DESCRIPTION": _("TODO"),
    "VERSION": settings.RESEARCHER_API_VERSION,
    # TODO: remove this in favor for automated tag detection #478
    "TAGS": [
        {"name": "Documenten"},
        {"name": "Informatiecategorieën"},
        {"name": "Onderwerpen"},
        {"name": "Organisaties"},
        {"name": "Publicaties"},
        {"name": "Themas"},
    ],
}
