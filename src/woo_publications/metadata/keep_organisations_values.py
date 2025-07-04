from contextlib import contextmanager

from django.db import models, transaction

from .models import Organisation


@contextmanager
@transaction.atomic
def keep_organisations_values():
    organisations = list(
        Organisation.objects.filter(
            models.Q(is_actief=True) or ~models.Q(rsin="")
        ).values("pk", "is_actief", "rsin")
    )
    organisations_data = {
        organisation["pk"]: {
            "is_actief": organisation["is_actief"],
            "rsin": organisation["rsin"],
        }
        for organisation in organisations
    }

    try:
        yield
    finally:
        organisations = []

        if organisations_data:
            for organisation in Organisation.objects.filter(
                pk__in=organisations_data.keys()
            ).iterator():
                for key, value in organisations_data[organisation.pk].items():
                    setattr(organisation, key, value)
                organisations.append(organisation)

            Organisation.objects.bulk_update(organisations, ["is_actief", "rsin"])
