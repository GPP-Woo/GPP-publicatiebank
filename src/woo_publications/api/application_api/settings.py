from django.conf import settings
from django.utils.translation import gettext_lazy as _

custom_settings = {
    "SCHEMA_PATH_PREFIX_INSERT": "/api",
    "TITLE": "GPP Publications",
    "DESCRIPTION": _(
        """
## Documentation

The GPP-Publications API enables client applications to consult and manage
the publications of documents for transparency of governance. This API
documentation contains three logical 'domains'.

### Domains

**Metadata**

Publications and their related documents must have certain metadata attached
to them. The metadata endpoints allow client applications to retrieve (and
in some resources also create/update) the available metadata.

* [Organisations](#tag/Organisaties): known government organisations, such
  as municipalities, provices...
* [Information categories](#tag/Informatiecategorieen): the prescribed
  categories for the [DiWoo](https://standaarden.overheid.nl/diwoo/metadata)
  standard, optionally extended with organization-specific categories.
* [Themes](#tag/Themas): a tree structure of parent/child themes to further
  describe what publications are about

**Publications**

* [Publications](#tag/Publicaties): a publication is a logical unit of
  information to be made public. It may contain one or more documents.
  Metadata is typically attached to a publication rather than the contained
  documents.
* [Documents](#tag/Documenten): the actual files/documents that are being
  made public and will be indexed in the search engine(s).

**Catalogi API**

The [Catalogi API](#tag/Catalogi-API) endpoint(s) are an implementation
detail of how this API works. Client applications do not have to worry about
them.

They are required to be able to re-use the Documenten API for the actual
document file storage.

### Authentication

**API key**

The API endpoints require authentication, for which you need an API key. API
keys are managed in the admin interface (see the functional documentation).

Once you have an API key, ensure every request has the necessary header:

    Authorization: Token my-example-api-key

Replace `my-example-api-key` with your actual API key.

**Audit headers**

Additionally, most endpoints require request headers to be set for audit
purposes:

    Audit-User-ID: unique-identifier@example.com
    Audit-User-Representation: Alice B. Tables
    Audit-Remarks: Retrieving own publications

"""
    ),
    "VERSION": settings.API_VERSION,
    # TODO: remove this in favor for automated tag detection #478
    "TAGS": [
        {"name": "Catalogi API"},
        {"name": "Documenten"},
        {"name": "Informatiecategorieën"},
        {"name": "Inzage Procedure"},
        {"name": "Onderwerpen"},
        {"name": "Organisatie-eenheden"},
        {"name": "Organisaties"},
        {"name": "Publicaties"},
        {"name": "Themas"},
    ],
}
