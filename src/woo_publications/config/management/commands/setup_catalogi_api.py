import uuid
from argparse import RawDescriptionHelpFormatter

from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError
from django.core.management.base import DjangoHelpFormatter

from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from ...models import CatalogiSetupError, GlobalConfiguration

DOCUMENTS_API_PATH = "/documenten/api/v1/"
CATALOGI_API_PATH = "/catalogi/api/v1/"


class HelpFormatter(DjangoHelpFormatter, RawDescriptionHelpFormatter):
    pass


class Command(BaseCommand):
    help = """\
Set up the Catalogi API for an existing installation.

Steps:
  1. If no Catalogi API service is configured, create one from the
     Documents API service and configure it.
  2. Create the catalogus and the default informatieobjecttype.
  3. Reset the Information Categories and sync them and the Documents
     with the Catalogi API in the background.

Warning: step 1 only works with an Open Zaak Documents API.
"""

    def create_parser(self, prog_name, subcommand, **kwargs):
        kwargs.setdefault("formatter_class", HelpFormatter)
        return super().create_parser(prog_name, subcommand, **kwargs)

    def handle(self, **options):
        config = GlobalConfiguration.get_solo()

        if config.catalogus_url and config.default_iot_url:
            raise CommandError("The Catalogi API is already set up.")

        if config.catalogi_api_service is None:
            config.catalogi_api_service = self._create_catalogi_service(config)
            config.save(update_fields=("catalogi_api_service",))
            self.stdout.write(
                f"Configured Catalogi API service {config.catalogi_api_service}."
            )

        try:
            GlobalConfiguration.setup_catalogi_api()
        except CatalogiSetupError as err:
            raise CommandError(str(err)) from err

        self.stdout.write(
            "Catalogi API has been set up successfully. The Information Categories "
            "and Documents will now be processed in the background.",
            self.style.SUCCESS,
        )

    @staticmethod
    def _create_catalogi_service(config: GlobalConfiguration) -> Service:
        if (documents_service := config.documents_api_service) is None:
            raise CommandError("No Documents API service is configured.")

        if not documents_service.api_root.endswith(DOCUMENTS_API_PATH):
            raise CommandError(
                f"The Documents API root {documents_service.api_root} does not end "
                f"with {DOCUMENTS_API_PATH}, it doesn't look like Open Zaak."
            )

        # copy the documents service, including its credentials
        service = Service.objects.get(pk=documents_service.pk)
        service.pk = None
        service._state.adding = True
        service.uuid = uuid.uuid4()
        service.label = "Open Zaak Catalogi API"
        service.slug = "open-zaak-catalogi-api"
        service.api_type = APITypes.ztc
        service.api_root = (
            documents_service.api_root.removesuffix(DOCUMENTS_API_PATH)
            + CATALOGI_API_PATH
        )
        service.api_connection_check_path = ""

        try:
            service.full_clean()
        except ValidationError as err:
            raise CommandError(
                f"Could not create the Catalogi API service: {err}"
            ) from err

        service.save()
        return service
