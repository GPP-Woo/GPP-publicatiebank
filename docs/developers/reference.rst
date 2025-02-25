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
pushed to the GPP Zoeken API to be included in an Elastic Search index to power the
GPP Burgerportaal for search. When a resource is revoked, it is removed from the index
again.

Index operations (and by extension the interaction with GPP Zoeken) is done
asynchronously using Celery tasks, after the database transaction is committed.

Database schema
---------------

You can right-mouse button click and then click "open in new tab" to see the image
in full resolution.

.. graphviz:: _assets/db_schema.dot
