from django.core.management import BaseCommand

from ...replace_document_iot_objects import change_document_api_iots


class Command(BaseCommand):
    help = "Change all the IOT objects of the document in the Documents api."

    def handle(self, *args, **options):
        change_document_api_iots()
