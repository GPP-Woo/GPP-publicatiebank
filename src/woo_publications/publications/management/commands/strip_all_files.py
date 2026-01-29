from urllib.parse import urljoin

from django.core.management.commands import loaddata
from django.urls import reverse

import requests

from ...file_processing import strip_all_files


class Command(loaddata.Command):
    help = "Load organisations from fixture file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            action="store",
            required=True,
            help=(
                "The base url of this website (WOO-Publications) "
                "this is used to construct urls. Example: 'https://www.gpp_publications.nl'."
            ),
        )

    def handle(self, *args, **options):
        base_url = options["base_url"]

        # Check if the provided base_url is correct.
        try:
            test_url = urljoin(base_url, reverse("api:api-root"))
            response = requests.get(test_url)
            response.raise_for_status()
        except requests.RequestException:
            self.stdout.write(
                "The provided base_url does not lead to this website.",
                self.style.ERROR,
            )
            return

        try:
            counter = strip_all_files(base_url)
        except AssertionError as err:
            assert err.args
            self.stdout.write(err.args[0], self.style.ERROR)
            return

        self.stdout.write(
            f"{counter} documents scheduled to strip its metadata.", self.style.SUCCESS
        )
