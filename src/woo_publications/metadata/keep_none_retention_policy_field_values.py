from contextlib import contextmanager

from django.db import transaction
from django.db.models import Q

from .constants import INFORMATION_CATEGORY_FIXTURE_FIELDS
from .models import InformationCategory


@contextmanager
@transaction.atomic
def keep_none_retention_policy_field_values():
    ignore_fields = INFORMATION_CATEGORY_FIXTURE_FIELDS + ["id"]

    # filter out the IC fixture fields and id from the local fields of
    # the InformationCategory to dynamically determine which fields
    # we need to track the old data from and update.
    updatable_fields = [
        field.name
        for field in InformationCategory._meta.local_fields
        if field.name not in ignore_fields
    ]

    # bron_bewaartermijn is a required field which is blank by default
    # so if it is empty the retention fields hasn't been set yet and can
    # be ignored.
    information_categories_data = {
        ic.pk: {field: getattr(ic, field) for field in updatable_fields}
        for ic in InformationCategory.objects.filter(
            ~Q(bron_bewaartermijn="")
        ).iterator()
    }

    try:
        yield
    finally:
        information_categories: list[InformationCategory] = []

        if information_categories_data:
            for ic in InformationCategory.objects.filter(
                pk__in=information_categories_data.keys()
            ).iterator():
                for key, value in information_categories_data[ic.pk].items():
                    setattr(ic, key, value)
                information_categories.append(ic)

            InformationCategory.objects.bulk_update(
                information_categories, updatable_fields
            )
