.. _developers_reference:

Reference
=========

Technical reference documentation that may be useful.

Architecture
------------

The GPP Publicatiebank is set up as a rather simple RESTful JSON API, consisting of two
major parts:

* Metadata
* Publications

**Metadata**

The metadata endpoints allow reading (and in some cases writing) of metadata used by/in
publications, such as information categories (defined in legislation), available
organisations and themes.

Some of the metadata is defined by a national body and published in JSON+LD lists. These
are automatically distributed and loaded in GPP Publicatiebank instances. Via the admin,
custom items can be added and modified, but the official records may not be modified.

**Publications**

Publications are containers for documents - they hold metadata and one or more documents
that have been (or are in the process of) been made publicly accessible.

The metadata is stored in a relations database (see the schema below), while the actual
binary content of the documents is persisted in a Documenten API (VNG standard).
Typically, we leverage Open Zaak for this (in development).

Publication and document resources have a particular publication status - at the time of
writing these are ``concept``, ``published`` and ``revoked``. Published resources are
pushed to the GPP-zoeken API to be included in an Elastic Search index to power the
GPP Burgerportaal for search. When a resource is revoked, it is removed from the index
again.

Index operations (and by extension the interaction with GPP-zoeken) is done
asynchronously using Celery tasks, after the database transaction is committed.

Document uploads
----------------

Documents within a publication hold pointers to binary content, representing the actual
downloadable document being published. There are two ways to provide documents to the
publicatiebank. The publicatiebank persists these documents in a Documents API service,
which is :ref:`configured in the global settings <configuration_services_documents_api>`.

Direct uploads
~~~~~~~~~~~~~~

In its simplest form, frontends/users can upload a document from disk to the
publicatiebank. In this scenario, the metadata of the document must be created first,
after which the expected file parts must be uploaded. Multiple file parts can be
uploaded in parallel. The publicatiebank ensures the file is stored in the underlying
Documents API.

While the document is being uploaded, requests to the download endpoint will respond
with an HTTP 409 (Conflict) status.

Remote document retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~

Alternatively, a document can be retrieved from a(nother) Documents API.
GPP-publicatiebank will then proceed to download it and save a copy in its own
configured Documents API. The source system can then safely destroy the document as part
of archiving requirements.

Using this approach, the API client indicates that a document URL will be provided, and
it must provide the document URL where the file can be downloaded. GPP-publicatiebank
expects to receive binary content when retrieving this URL with a GET request, matching
the behaviour of the
`Documents API <https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/>`_
standard.

The download from the remote URL and upload to the own Documents API take place in a
background job. While this job is pending, attempting to download the document will
result in an HTTP 409 (Conflict) response.

Clients can refresh/poll the ``Document`` detail endpoint and check the
``uploadComplete`` property.

.. note:: Any services/endpoints from which documents may be downloaded *must* be
   registered in the :ref:`admin interface <configuration_services>` *before*
   attempting to use them, so that:

   * the API credentials have been sorted out
   * server-side request forgeries are mitigated

Database schema
---------------

You can right-mouse button click and then click "open in new tab" to see the image
in full resolution.

.. graphviz:: _assets/db_schema.dot
