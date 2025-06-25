from django.db import models
from django.utils.translation import gettext_lazy as _


class PublicationStatusOptions(models.TextChoices):
    published = "gepubliceerd", _("Published")
    concept = "concept", _("Concept")
    revoked = "ingetrokken", _("Revoked")


class DocumentDeliveryMethods(models.TextChoices):
    receive_upload = "ontvangen", _("Receive")  # client uploads file to use
    retrieve_url = "ophalen", _("Retrieve")  # we download the file from a provided URL
