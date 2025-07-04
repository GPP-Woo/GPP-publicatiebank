import uuid

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from ordered_model.models import OrderedModel
from treebeard.mp_tree import MP_Node

from woo_publications.config.validators import validate_rsin
from woo_publications.constants import ArchiveNominationChoices

from .constants import InformationCategoryOrigins, OrganisationOrigins
from .managers import InformationCategoryManager, OrganisationManager, ThemeManager

CUSTOM_CATEGORY_IDENTIFIER_URL_PREFIX = (
    "https://generiek-publicatieplatform.woo/informatiecategorie/"
)

CUSTOM_ORGANISATION_URL_PREFIX = "https://generiek-publicatieplatform.woo/organisation/"

CUSTOM_THEME_URL_PREFIX = "https://generiek-publicatieplatform.woo/thema/"


def get_default_information_category_identifier():
    return f"{CUSTOM_CATEGORY_IDENTIFIER_URL_PREFIX}{uuid.uuid4()}"


def get_default_organisation_identifier():
    return f"{CUSTOM_ORGANISATION_URL_PREFIX}{uuid.uuid4()}"


def get_default_theme_identifier():
    return f"{CUSTOM_THEME_URL_PREFIX}{uuid.uuid4()}"


class InformationCategory(OrderedModel):
    uuid = models.UUIDField(_("UUID"), unique=True, default=uuid.uuid4)
    identifier = models.URLField(
        _("identifier"),
        help_text=_(
            "The unique IRI that identifies this category in the overheid.nl value "
            "list. For entries that have been added manually, an identifier is "
            "generated."
        ),
        max_length=255,
        unique=True,
        editable=False,
        default=get_default_information_category_identifier,
    )
    naam = models.CharField(_("name"), max_length=80)
    naam_meervoud = models.CharField(_("name plural"), max_length=80, blank=True)
    definitie = models.TextField(_("definition"), blank=True)
    oorsprong = models.CharField(
        _("origin"),
        help_text=_(
            "Determines where the category is defined and sourced from, and how "
            "the identifier should be interpreted. If the value list is the origin, "
            "the category can not be modified or deleted."
        ),
        choices=InformationCategoryOrigins.choices,
        blank=False,
        max_length=15,
        default=InformationCategoryOrigins.custom_entry,
    )
    # Optional fields:
    omschrijving = models.TextField(
        _("description"),
        help_text=_("The brief explanation shown to employees and citizens."),
        blank=True,
    )
    # Retention fields:
    bron_bewaartermijn = models.CharField(
        _("retention policy source"),
        help_text=_(
            "The source of the retention policy (example: Selectielijst "
            "gemeenten 2020)."
        ),
        max_length=255,
        blank=False,
        default="",
    )
    selectiecategorie = models.CharField(
        _("selection category"),
        help_text=_(
            "The category as specified in the provided retention policy source "
            "(example: 20.1.2)."
        ),
        max_length=255,
        blank=True,
    )
    archiefnominatie = models.CharField(
        _("archive action"),
        help_text=_("Determines if the archived data will be retained or disposed."),
        choices=ArchiveNominationChoices.choices,
        max_length=50,
        blank=False,
        default=ArchiveNominationChoices.retain,
    )
    bewaartermijn = models.PositiveIntegerField(
        _("retention period"),
        help_text=_("The retention period in years."),
        validators=[MaxValueValidator(999)],
        default=10,
        blank=False,
    )
    toelichting_bewaartermijn = models.TextField(
        _("retention policy explanation"),
        blank=True,
    )

    objects = InformationCategoryManager()

    class Meta(OrderedModel.Meta):
        verbose_name = _("information category")
        verbose_name_plural = _("information categories")

    def __str__(self):
        return self.naam

    def natural_key(self):
        return (self.identifier,)


class Theme(MP_Node):
    uuid = models.UUIDField(_("UUID"), unique=True, default=uuid.uuid4)
    identifier = models.URLField(
        _("identifier"),
        help_text=_(
            "The unique IRI that identifies this theme in the overheid.nl value list. "
            "For entries that have been added manually, an identifier is generated."
        ),
        max_length=255,
        unique=True,
        editable=False,
        default=get_default_theme_identifier,
    )
    naam = models.CharField(_("name"), max_length=80)

    node_order_by = ("naam",)

    objects = ThemeManager()

    class Meta:  # pyright: ignore
        verbose_name = _("theme")
        verbose_name_plural = _("themes")

    def __str__(self):
        return self.naam

    def natural_key(self):
        return (self.identifier,)


class Organisation(models.Model):
    uuid = models.UUIDField(_("UUID"), unique=True, default=uuid.uuid4)
    identifier = models.URLField(
        _("identifier"),
        help_text=_(
            "The unique IRI that identifies this organisation in the overheid.nl value "
            "list. For entries that have been added manually, an identifier is "
            "generated."
        ),
        max_length=255,
        unique=True,
        editable=False,
        default=get_default_organisation_identifier,
    )
    naam = models.CharField(_("name"), max_length=255)
    oorsprong = models.CharField(
        _("origin"),
        help_text=_(
            "Determines where the organisation is defined and sourced from, and how "
            "the identifier should be interpreted. If the value list is the origin, "
            "the organisation can not be modified or deleted."
        ),
        choices=OrganisationOrigins.choices,
        blank=False,
        max_length=15,
        default=OrganisationOrigins.custom_entry,
    )
    # custom fields
    rsin = models.CharField(
        _("RSIN"),
        max_length=9,
        help_text=_("The RSIN of the organisation."),
        validators=[validate_rsin],
        blank=True,
    )
    is_actief = models.BooleanField(
        _("is active"),
        help_text=_("Displays if the the organisation is currently active or not."),
        default=False,
        null=False,
    )

    objects = OrganisationManager()

    class Meta:
        verbose_name = _("organisation")
        verbose_name_plural = _("organisations")

    def __str__(self):
        return self.naam

    def natural_key(self):
        return (self.identifier,)
