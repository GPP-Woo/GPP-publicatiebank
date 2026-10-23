from contextlib import contextmanager
from functools import partial

from django.db import transaction

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from woo_publications.config.models import GlobalConfiguration

from .constants import INFORMATION_CATEGORY_FIXTURE_FIELDS
from .models import InformationCategory
from .tasks import index_iot, update_iot_description


@contextmanager
@transaction.atomic
def keep_none_retention_policy_field_values():
    # initialize catalogi API information
    config = GlobalConfiguration.get_solo()

    ignore_fields = INFORMATION_CATEGORY_FIXTURE_FIELDS + ["id"]

    # filter out the IC fixture fields and id from the local fields of
    # the InformationCategory to dynamically determine which fields
    # we need to track the old data from and update.
    updatable_fields = [
        field.name
        for field in InformationCategory._meta.local_fields
        if field.name not in ignore_fields
    ]

    # Since we deleted the catalogi API endpoint from the project
    # we now track the URL in the database table itself.
    # because of it we always have keep track of the original data
    # of specific fields, to ensure we don't delete the lookups.
    information_categories_edital_data = {
        ic.pk: {field: getattr(ic, field) for field in updatable_fields}
        for ic in InformationCategory.objects.iterator()
    }

    # Tracking the original names of the ICs to see if it has changed
    # if it has changed then we need to update the attached IOT in the
    # catalogi API.
    information_categories_name = {}
    if config.catalogi_api_service:
        information_categories_name = {
            ic.pk: ic.naam for ic in InformationCategory.objects.iterator()
        }

    try:
        yield
    finally:
        information_categories: list[InformationCategory] = []

        # retain original data
        if information_categories_edital_data:
            for ic in InformationCategory.objects.filter(
                pk__in=information_categories_edital_data.keys()
            ).iterator():
                for key, value in information_categories_edital_data[ic.pk].items():
                    setattr(ic, key, value)
                information_categories.append(ic)

            InformationCategory.objects.bulk_update(
                information_categories, updatable_fields
            )

        if config.catalogi_api_service:
            for ic in InformationCategory.objects.iterator():
                if not ic.iot_url:
                    transaction.on_commit(
                        partial(
                            index_iot.delay,
                            information_category_id=ic.pk,
                            confidentiality_indication=VertrouwelijkheidsAanduidingen.openbaar,
                        )
                    )
                    continue

                if ic.naam != information_categories_name[ic.pk]:
                    transaction.on_commit(
                        partial(
                            update_iot_description.delay, information_category_id=ic.pk
                        )
                    )
