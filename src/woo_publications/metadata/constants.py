from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

INFORMATION_CATEGORY_FIXTURE_FIELDS = [
    "order",
    "uuid",
    "identifier",
    "naam",
    "naam_meervoud",
    "definitie",
    "oorsprong",
]


class InformationCategoryOrigins(TextChoices):
    value_list = "waardelijst", _("Value list")
    custom_entry = "zelf_toegevoegd", _("Custom entry")


class OrganisationOrigins(TextChoices):
    municipality_list = "gemeentelijst", _("Municipality list")
    so_list = "solijst", _("Collaborative organisations list")
    oorg_list = "oorglijst", _("Alternative government organisations")
    custom_entry = "zelf_toegevoegd", _("Custom entry")
