from django.core.management.commands import loaddata

from ...keep_none_retention_policy_field_values import (
    keep_none_retention_policy_field_values,
)


class Command(loaddata.Command):
    help = "Load information categories from fixture file"

    def handle(self, *args, **options):
        with keep_none_retention_policy_field_values():
            super().handle(*args, **options)
