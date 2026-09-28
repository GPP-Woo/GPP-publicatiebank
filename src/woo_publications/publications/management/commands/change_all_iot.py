from django.core.management import BaseCommand

from ...change_all_iot import change_all_iot


class Command(BaseCommand):
    help = "Change all the IOT objects of the document in the Documents api."

    def handle(self, *args, **options):
        change_all_iot()
