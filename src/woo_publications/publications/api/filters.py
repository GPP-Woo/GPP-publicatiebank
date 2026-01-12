from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import FilterSet, filters
from django_filters.widgets import CSVWidget

from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.constants import InformationCategoryOrigins
from woo_publications.metadata.models import InformationCategory

from ..constants import PublicationStatusOptions
from ..models import Document, Publication, Topic


def _filter_informatie_categorieen(
    queryset: QuerySet, name: str, value: list[InformationCategory] | None
) -> QuerySet:
    if not value:
        return queryset

    qs = Q(**{f"{name}__in": value})

    if settings.INSPANNINGSVERPLICHTING_IDENTIFIER in [ic.identifier for ic in value]:
        qs |= Q(**{f"{name}__oorsprong": InformationCategoryOrigins.custom_entry})

    return queryset.filter(qs)


class DocumentFilterSet(FilterSet):
    # TODO: change this filter to custom named filter with `@extend_schema_field(UUID)`
    publicatie = filters.ModelChoiceFilter(
        queryset=Publication.objects.all(),
        to_field_name="uuid",
        help_text=_(
            "Search the document based on the unique identifier (UUID) that represents "
            "a publication. **Disclaimer**: disregard the documented type `integer` "
            "the correct type is `UUID`."
        ),
    )
    registratiedatum_vanaf = filters.DateTimeFilter(
        help_text=_(
            "Filter documents that were registered after or on the given value."
        ),
        field_name="registratiedatum",
        lookup_expr="gte",
    )
    registratiedatum_tot = filters.DateTimeFilter(
        help_text=_("Filter documents that were registered before the given value."),
        field_name="registratiedatum",
        lookup_expr="lt",
    )
    registratiedatum_tot_en_met = filters.DateTimeFilter(
        help_text=_(
            "Filter documents that were registered before or on the given value."
        ),
        field_name="registratiedatum",
        lookup_expr="lte",
    )
    creatiedatum_vanaf = filters.DateFilter(
        help_text=_("Filter documents that were created after or on the given value."),
        field_name="creatiedatum",
        lookup_expr="gte",
    )
    creatiedatum_tot = filters.DateFilter(
        help_text=_("Filter documents that were created before the given value."),
        field_name="creatiedatum",
        lookup_expr="lt",
    )
    creatiedatum_tot_en_met = filters.DateFilter(
        help_text=_("Filter documents that were created before or on the given value."),
        field_name="creatiedatum",
        lookup_expr="lte",
    )
    laatst_gewijzigd_datum_vanaf = filters.DateTimeFilter(
        help_text=_(
            "Filter documents that were last modified after or on the given value."
        ),
        field_name="laatst_gewijzigd_datum",
        lookup_expr="gte",
    )
    laatst_gewijzigd_datum_tot = filters.DateTimeFilter(
        help_text=_("Filter documents that were last modified before the given value."),
        field_name="laatst_gewijzigd_datum",
        lookup_expr="lt",
    )
    laatst_gewijzigd_datum_tot_en_met = filters.DateTimeFilter(
        help_text=_(
            "Filter documents that were last modified before or on the given value."
        ),
        field_name="laatst_gewijzigd_datum",
        lookup_expr="lte",
    )
    eigenaar = filters.CharFilter(
        help_text=_("Filter documents based on the owner identifier of the object."),
        field_name="eigenaar__identifier",
        lookup_expr="exact",
    )
    publicatiestatus = filters.MultipleChoiceFilter(
        help_text=_("Filter documents based on the publication status."),
        choices=PublicationStatusOptions.choices,
        widget=CSVWidget(),
    )
    identifier = filters.CharFilter(
        help_text="Search the document based on the identifier field.",
    )
    informatie_categorieen = filters.ModelMultipleChoiceFilter(
        help_text=_(
            "Filter documents that belong to a particular information category. "
            "When you specify multiple categories, documents belonging to any "
            "category are returned.\n\n"
            "Filter values should be the UUID of the categories."
        ),
        field_name="publicatie__informatie_categorieen",
        to_field_name="uuid",
        queryset=InformationCategory.objects.all(),
        widget=CSVWidget(),
        method=_filter_informatie_categorieen,
    )
    sorteer = filters.OrderingFilter(
        help_text=_("Order on."),
        fields=(
            "creatiedatum",
            "officiele_titel",
            "verkorte_titel",
        ),
    )

    class Meta:
        model = Document
        fields = (
            "publicatie",
            "eigenaar",
            "publicatiestatus",
            "identifier",
            "registratiedatum_vanaf",
            "registratiedatum_tot",
            "registratiedatum_tot_en_met",
            "creatiedatum_vanaf",
            "creatiedatum_tot",
            "creatiedatum_tot_en_met",
            "laatst_gewijzigd_datum_vanaf",
            "laatst_gewijzigd_datum_tot",
            "laatst_gewijzigd_datum_tot_en_met",
            "sorteer",
        )


class PublicationFilterSet(FilterSet):
    search = filters.CharFilter(
        help_text=_("Searches publications based on the official and short title."),
        method="search_official_and_short_title",
    )
    eigenaar = filters.CharFilter(
        help_text=_("Filter publications based on the owner identifier of the object."),
        field_name="eigenaar__identifier",
        lookup_expr="exact",
    )
    eigenaar_groep = filters.CharFilter(
        help_text=_(
            "Filter publications based on the owner group identifier of the object."
        ),
        field_name="eigenaar_groep__identifier",
        lookup_expr="exact",
    )
    publicatiestatus = filters.MultipleChoiceFilter(
        help_text=_("Filter publications based on the publication status."),
        choices=PublicationStatusOptions.choices,
        widget=CSVWidget(),
    )
    kenmerk = filters.CharFilter(
        help_text=_("Filter publications based on the given identifier."),
        field_name="publicationidentifier__kenmerk",
        lookup_expr="exact",
    )
    bron = filters.CharFilter(
        help_text=_("Filter publications based on the given identifier source."),
        field_name="publicationidentifier__bron",
        lookup_expr="exact",
    )
    archiefnominatie = filters.MultipleChoiceFilter(
        help_text=_("Filter publications based on the archiefnominatie."),
        choices=ArchiveNominationChoices.choices,
    )
    registratiedatum_vanaf = filters.DateTimeFilter(
        help_text=_(
            "Filter publications that were registered after or on the given value."
        ),
        field_name="registratiedatum",
        lookup_expr="gte",
    )
    registratiedatum_tot = filters.DateTimeFilter(
        help_text=_("Filter publications that were registered before the given value."),
        field_name="registratiedatum",
        lookup_expr="lt",
    )
    registratiedatum_tot_en_met = filters.DateTimeFilter(
        help_text=_(
            "Filter publications that were registered before or on the given value."
        ),
        field_name="registratiedatum",
        lookup_expr="lte",
    )
    archiefactiedatum_vanaf = filters.DateTimeFilter(
        help_text=_(
            "Filter publications where the archive action date is after or on the "
            "given value."
        ),
        field_name="archiefactiedatum",
        lookup_expr="gte",
    )
    archiefactiedatum_tot = filters.DateTimeFilter(
        help_text=_(
            "Filter publications where the archive action date is before the "
            "given value."
        ),
        field_name="archiefactiedatum",
        lookup_expr="lt",
    )
    archiefactiedatum_tot_en_met = filters.DateTimeFilter(
        help_text=_(
            "Filter publications where the archive action date is before or on the "
            "given value."
        ),
        field_name="archiefactiedatum",
        lookup_expr="lte",
    )
    informatie_categorieen = filters.ModelMultipleChoiceFilter(
        help_text=_(
            "Filter publications that belong to a particular information category. "
            "When you specify multiple categories, publications belonging to any "
            "category are returned.\n\n"
            "Filter values should be the UUID of the categories."
        ),
        field_name="informatie_categorieen",
        to_field_name="uuid",
        queryset=InformationCategory.objects.all(),
        widget=CSVWidget(),
        method=_filter_informatie_categorieen,
    )
    onderwerpen = filters.ModelMultipleChoiceFilter(
        help_text=_(
            "Filter publications that belong to a particular topic. "
            "When you specify multiple topics, publications belonging to any "
            "topic are returned.\n\n"
            "Filter values should be the UUID of the topics."
        ),
        field_name="onderwerpen__uuid",
        to_field_name="uuid",
        queryset=Topic.objects.all(),
        widget=CSVWidget(),
    )

    sorteer = filters.OrderingFilter(
        help_text=_("Order on."),
        fields=(
            "registratiedatum",
            "officiele_titel",
            "verkorte_titel",
        ),
    )

    class Meta:
        model = Publication
        fields = (
            "search",
            "eigenaar",
            "eigenaar_groep",
            "publicatiestatus",
            "kenmerk",
            "bron",
            "informatie_categorieen",
            "onderwerpen",
            "archiefnominatie",
            "registratiedatum_vanaf",
            "registratiedatum_tot",
            "registratiedatum_tot_en_met",
            "archiefactiedatum_vanaf",
            "archiefactiedatum_tot",
            "archiefactiedatum_tot_en_met",
            "sorteer",
        )

    def filter_queryset(self, queryset):
        """
        Exclude the fields to OR-match rather than AND and apply separately.
        """
        owner = self.form.cleaned_data.pop("eigenaar", None)
        owner_group = self.form.cleaned_data.pop("eigenaar_groep", None)
        queryset = super().filter_queryset(queryset)

        # build the OR-filter - see django_filters.filters.Filter.filter for the ref
        or_q = Q()
        for name, value in (
            ("eigenaar", owner),
            ("eigenaar_groep", owner_group),
        ):
            if value in EMPTY_VALUES:
                continue
            filter = self.filters[name]
            assert not filter.distinct
            lookup = f"{filter.field_name}__{filter.lookup_expr}"
            or_q |= Q(**{lookup: value})
        queryset = queryset.filter(or_q)

        return queryset

    def search_official_and_short_title(self, queryset, name: str, value: str):
        return queryset.filter(
            Q(officiele_titel__icontains=value) | Q(verkorte_titel__icontains=value)
        )


class TopicFilterSet(FilterSet):
    publicaties = filters.ModelMultipleChoiceFilter(
        help_text=_(
            "Filter topics that belong to a publication. "
            "When you specify multiple publications, topics belonging to any "
            "publication are returned.\n\n"
            "Filter values should be the UUID of the publications."
        ),
        field_name="publication__uuid",
        to_field_name="uuid",
        queryset=Publication.objects.all(),
        widget=CSVWidget(),
    )
    publicatiestatus = filters.MultipleChoiceFilter(
        help_text=_("Filter topics based on the publication status."),
        choices=PublicationStatusOptions.choices,
        widget=CSVWidget(),
    )
