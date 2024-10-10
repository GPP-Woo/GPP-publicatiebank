from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...theme_sync import ThemeWaardenlijstError, update_theme


class Command(BaseCommand):
    help = "Retrieve the themes from the value list published on overheid.nl and dump them as a fixture."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file-path",
            action="store",
            help="The file path to where the fixture file will be created.",
            default=Path(
                settings.DJANGO_PROJECT_DIR / "fixtures" / "themes.json",
            ),
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        try:
            update_theme(file_path)
        except ThemeWaardenlijstError as err:
            raise CommandError(err.message) from err
