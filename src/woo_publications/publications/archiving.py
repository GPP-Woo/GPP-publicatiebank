from django.db.models import QuerySet

from woo_publications.constants import ArchiveNominationChoices
from woo_publications.metadata.models import InformationCategory


def get_retention_informatie_category(
    informatie_categorieen: QuerySet[InformationCategory],
) -> InformationCategory | None:
    """
    Determine the most appropriate inf. category for archiving parameter derivation.

    The following logic is applied:

    - Information categories with :arg:`archiefnominatie` ``retain`` will always be
      used if present.
    - When the archiefnominatie is ``retain``, then return the Information Category
      with the lowest ``bewaartermijn``
    - When the archiefnominatie is ``dispose``, then return the Information Category
      with the highest ``bewaartermijn``

    .. note:: we use the order of the Information Category as the leading factor when
       multiple information categories have the same bewaartermijn.
    """

    if len(informatie_categorieen) <= 1:
        return informatie_categorieen.first()

    retain = any(
        ic.archiefnominatie == ArchiveNominationChoices.retain
        for ic in informatie_categorieen
    )
    if retain:
        return (
            informatie_categorieen.filter(
                archiefnominatie=ArchiveNominationChoices.retain
            )
            .order_by("bewaartermijn", "order")
            .first()
        )

    return (
        informatie_categorieen.filter(archiefnominatie=ArchiveNominationChoices.destroy)
        .order_by("-bewaartermijn", "order")
        .first()
    )
