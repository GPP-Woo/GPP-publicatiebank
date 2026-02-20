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
    caribbean_list = "caribischelijst", _("Caribbean organisations")
    province_list = "provincielijst", _("Province list")
    water_board_list = "waterschaplijst", _("Water Board list")
    zbo_list = "zbolijst", _("ZBO list")
    custom_entry = "zelf_toegevoegd", _("Custom entry")
