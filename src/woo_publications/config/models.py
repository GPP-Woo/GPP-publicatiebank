from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes

from .validators import validate_rsin


class GlobalConfiguration(SingletonModel):
    """
    Global configuration settings managed via the admin.

    .. note:: This models a shortcut where we currently only support a single
       Documents API. Our database can handle multiple, but a mechanism to specify/route
       this is currently out of scope.
    """

    documents_api_service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.PROTECT,
        limit_choices_to={"api_type": APITypes.drc},
        verbose_name=_("Documents API service"),
        help_text=_(
            "The service to use for new document uploads - the metadata and binary "
            "content will be sent to this API."
        ),
        null=True,
        blank=False,
        related_name="+",
    )
    organisation_rsin = models.CharField(
        _("organisation RSIN"),
        max_length=9,
        help_text=_(
            "The RSIN of the municipality that owns the documents in the Documents API."
        ),
        validators=[validate_rsin],
    )

    gpp_search_service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.PROTECT,
        limit_choices_to={"api_type": APITypes.orc},
        verbose_name=_("GPP Search service"),
        help_text=_(
            "The service to use for search index operations to make the content "
            "publicly available."
        ),
        null=True,
        blank=False,
        related_name="+",
    )
    gpp_app_publication_url_template = models.URLField(
        _("GPP-app publication URL template"),
        max_length=500,
        default="",
        blank=True,
        help_text=_(
            "URL pattern to a publication in the GPP app. The special token <UUID> "
            "will be replaced with the system identifier of each publication."
        ),
    )
    gpp_burgerportaal_publication_url_template = models.URLField(
        _("GPP-burgerportaal publication URL template"),
        max_length=500,
        default="",
        blank=True,
        help_text=_(
            "URL pattern to a publication in the GPP burgerportaal. The special "
            "token <UUID> will be replaced with the system identifier of each "
            "publication."
        ),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("global configuration")

    def __str__(self) -> str:
        return force_str(self._meta.verbose_name)
