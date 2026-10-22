from django.db import models, transaction
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from woo_publications.contrib.catalogi_api.client import CatalogiAPIError, get_client

from .validators import validate_rsin


class CatalogiSetupError(Exception):
    """
    The Catalogi API objects could not be set up.

    The message is meant to be shown to the user.
    """


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
        verbose_name=_("documents API service"),
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
    document_meta_data_stripping = models.BooleanField(
        _("strip document metadata"),
        help_text=_("Enable the meta data stripping functionality of documents."),
        default=True,
    )

    catalogi_api_service = models.ForeignKey(
        "zgw_consumers.Service",
        on_delete=models.PROTECT,
        limit_choices_to={"api_type": APITypes.ztc},
        verbose_name=_("catalogi API service"),
        help_text=_("The service to use for informatieobjecttype objects."),
        null=True,
        blank=False,
        related_name="+",
    )
    catalogus_url = models.URLField(
        verbose_name=_("catalogus url"),
        help_text=_(
            "The URL to the catalogus object. This field will be automatically "
            "generated if no data is provided, this means to generate it again when "
            "switching services you have to empty the field yourself. Disclaimer: "
            "A catalogus should be unique (per service) based on the RSIN, if you "
            "switch back and forth between services our application won't be able to "
            "generate the catalogus url. If you want to switch back you should provide "
            "the url manually."
        ),
        blank=True,
    )
    default_iot_url = models.URLField(
        verbose_name=_("default informatieobjecttype url"),
        help_text=_(
            "The URL to the default informatieobjecttype object. "
            "This field will be automatically generated if no data is provided, "
            "this means to generate it again when switching services you have to "
            "empty the field yourself."
        ),
        blank=True,
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
    perspective_reaction_form_url = models.URLField(
        _("perspective reaction form URL"),
        max_length=500,
        help_text=_("The URL to the default perspective reaction form."),
    )
    objection_reaction_form_url = models.URLField(
        _("objection reaction form URL"),
        max_length=500,
        help_text=_("The URL to the default objection reaction form."),
    )

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("global configuration")
        constraints = [
            models.CheckConstraint(
                check=models.Q(catalogus_url__gt="") | models.Q(default_iot_url=""),
                name="catalogi_api_reference",
                violation_error_message=_(
                    "The default IOT URL field cannot be set if the Catalogi URL "
                    "field is empty."
                ),
            )
        ]

    def __str__(self) -> str:
        return force_str(self._meta.verbose_name)

    @classmethod
    def setup_catalogi_api(cls) -> None:
        """
        Create the catalogus and default IOT in the configured Catalogi API.

        Once committed, the Information Categories are reset and the
        Information Categories and Documents are synced with the Catalogi API in the
        background. A catalogus created before a failure is kept.

        :raises CatalogiSetupError: when (part of) the setup failed.
        """
        with transaction.atomic():
            config = cls.objects.select_for_update().get(pk=cls.singleton_instance_id)
            try:
                config._create_catalogi_api_objects()
            except CatalogiSetupError as err:
                error = err
            else:
                error = None
                transaction.on_commit(_sync_models_with_catalogi_api)
            config.save(update_fields=("catalogus_url", "default_iot_url"))

        if error is not None:
            raise error

    def _create_catalogi_api_objects(self) -> None:
        service = self.catalogi_api_service

        if service is None or service.connection_check != 200:
            raise CatalogiSetupError(
                _(
                    "The Catalogi API service is not available. "
                    "Because of this the Catalogi and default Informationobjecttypes "
                    "couldn't be created. Check if you configured the Service "
                    "correctly and make sure that it is running correctly."
                )
            )

        with get_client(service) as client:
            if not self.catalogus_url:
                try:
                    self.catalogus_url = client.create_catalogi(
                        rsin=self.organisation_rsin
                    )
                except CatalogiAPIError as err:
                    raise CatalogiSetupError(
                        _("Something went wrong while trying to create the Catalogi.")
                    ) from err

            try:
                iot = client.create_iot(
                    description=(
                        "informatieobjecttypen of publications with no information "
                        "category objects."
                    ),
                    catalogus=self.catalogus_url,
                    confidentiality_indication=VertrouwelijkheidsAanduidingen.vertrouwelijk,
                )
            except CatalogiAPIError as err:
                raise CatalogiSetupError(
                    _(
                        "Something went wrong while trying to create the default "
                        "Informationobjecttypes."
                    )
                ) from err

        self.default_iot_url = iot.url


def _sync_models_with_catalogi_api() -> None:
    # avoid circular imports, both modules depend on this one
    from woo_publications.metadata.models import InformationCategory

    from .tasks import sync_information_categories_and_documents_with_catalog_api

    InformationCategory.objects.update(iot_url="", iot_uuid=None)
    sync_information_categories_and_documents_with_catalog_api.delay(
        confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar
    )
