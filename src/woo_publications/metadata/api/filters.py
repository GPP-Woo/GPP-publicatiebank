from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from django_filters.rest_framework import FilterSet

from woo_publications.api.filters import URLFilter

from ..constants import OrganisationOrigins
from ..models import InformationCategory, Organisation


class OrganisationActive(TextChoices):
    active = "true", _("Retrieves all the active organisations (default)")
    inactive = "false", _("Retrieves all the inactive organisations")
    all = "alle", _("Retrieve every organisation regardless if active or inactive.")


class InformationCategoryFilterSet(FilterSet):
    identifier = URLFilter(
        lookup_expr="exact",
        help_text=_(
            "Search the information category based on the unique IRI that identifies "
            "a specific category."
        ),
    )
    naam = filters.CharFilter(
        lookup_expr="icontains",
        help_text=_(
            "Search the information category based on the name of the category."
        ),
    )

    class Meta:
        model = InformationCategory
        fields = (
            "identifier",
            "naam",
        )


class OrganisationFilterSet(FilterSet):
    identifier = URLFilter(
        lookup_expr="exact",
        help_text=_(
            "Search the organisations by the unique IRI that identifies a "
            "specific organisation."
        ),
    )
    naam = filters.CharFilter(
        lookup_expr="icontains",
        help_text=_(
            "Search through the organisations based on the name of the organisation. "
            "You can search on parts of the name, and matching is case-insensitive."
        ),
    )
    oorsprong = filters.ChoiceFilter(
        choices=OrganisationOrigins.choices,
        help_text=_("Search the organisation based on the origin of the organisation."),
    )
    is_actief = filters.ChoiceFilter(
        choices=OrganisationActive.choices,
        method="filter_is_actief",
        help_text=_("Filter the organisations depending on their activity status:"),
    )

    class Meta:
        model = Organisation
        fields = (
            "identifier",
            "naam",
            "oorsprong",
            "is_actief",
        )

    def filter_is_actief(self, queryset, name: str, value: str):
        # NOTE: this method does not get called if no filter param is used. The
        # default filtering case is implemented in the respective viewset method.
        match value:
            case OrganisationActive.inactive:
                return queryset.filter(is_actief=False)
            case OrganisationActive.all:
                return queryset
            case _:
                return queryset.filter(is_actief=True)
