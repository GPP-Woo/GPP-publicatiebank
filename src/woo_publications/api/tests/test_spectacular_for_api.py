from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

from parametrize.parametrize import parametrize


class SpectacularForApiTestCase(SimpleTestCase):
    @parametrize("component", ["application", "reuse"])
    def test_oas_generation(self, component: str):
        oas_file = (
            Path(settings.DJANGO_PROJECT_DIR)
            / "api"
            / f"{component}_api"
            / "openapi.yaml"
        )

        with NamedTemporaryFile(mode="w+", suffix=".yaml") as file:
            call_command(
                "spectacular_for_api",
                "--file",
                file.name,
                "--lang",
                "nl-nl",
                "--validate",
                "--component",
                f"{component}_api",
            )
            file.seek(0)
            self.assertEqual(file.read(), oas_file.read_text())
