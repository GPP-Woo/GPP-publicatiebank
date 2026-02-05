from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ArchiveNominationChoices(TextChoices):
    retain = "blijvend_bewaren", _("Retain")
    destroy = "vernietigen", _("Dispose")


class StrippableFileTypes(TextChoices):
    pdf = "pdf", _("PDF File")
    open_document = "open_document", _("Open Document")


# https://mimetype.io/all-types
OPENDOCUMENTS = [
    (".odc", "application/vnd.oasis.opendocument.chart"),
    (".otc", "application/vnd.oasis.opendocument.chart-template"),
    (".odb", "application/vnd.oasis.opendocument.database"),
    (".odf", "application/vnd.oasis.opendocument.formula"),
    (".odft", "application/vnd.oasis.opendocument.formula-template"),
    (".odg", "application/vnd.oasis.opendocument.graphics"),
    (".odgt", "application/vnd.oasis.opendocument.graphics-template"),
    (".odi", "application/vnd.oasis.opendocument.image"),
    (".odit", "application/vnd.oasis.opendocument.image-template"),
    (".odp", "application/vnd.oasis.opendocument.presentation"),
    (".odpt", "application/vnd.oasis.opendocument.presentation-template"),
    (".ods", "application/vnd.oasis.opendocument.spreadsheet"),
    (".odst", "application/vnd.oasis.opendocument.spreadsheet-template"),
    (".odt", "application/vnd.oasis.opendocument.text"),
    (".otm", "application/vnd.oasis.opendocument.text-master"),
    (".ott", "application/vnd.oasis.opendocument.text-template"),
    (".oth", "application/vnd.oasis.opendocument.text-web"),
]
