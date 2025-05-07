from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...organisation_sync import OrganisatieWaardenlijstError, update_organisation


class Command(BaseCommand):
    help = (
        "Retrieve the organisations from the value lists published on overheid.nl "
        "and dump them as a fixture."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file-path",
            action="store",
            help="The file path to where the fixture file will be created.",
            default=Path(
                settings.DJANGO_PROJECT_DIR / "fixtures" / "organisations.json",
            ),
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        try:
            update_organisation(file_path)
        except OrganisatieWaardenlijstError as err:
            raise CommandError(err.message) from err
