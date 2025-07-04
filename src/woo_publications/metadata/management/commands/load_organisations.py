from django.core.management.commands import loaddata

from ...keep_organisations_values import keep_organisations_values


class Command(loaddata.Command):
    help = "Load organisations from fixture file"

    def handle(self, *args, **options):
        with keep_organisations_values():
            super().handle(*args, **options)
