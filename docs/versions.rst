.. _versions:

Versioning
==========

Policy
------

GPP-Publicatiebank (and the associated API spefication) adheres to
`semantic versioning <https://semver.org/>`_, meaning major versions may introduce
breaking changes and minor versions are backwards compatible. Release notes for each
version are documented in the :ref:`changelog`.

The version of the backend and its API specification are not guaranteed to be the same -
bugfixes and improvements can result in a newer version of the backend compared to the
shipped API specification. A version bump in the API specification always implies a
version bump of the backend.

Backend and API
---------------

The backend contains the storage and exposes the API.

.. table:: API version offered by backend version
   :widths: auto

   =============== ===========
   Backend version API version
   =============== ===========
   1.2.0           1.1.0
   1.1.0           1.0.0
   1.0.0           1.0.0
   =============== ===========

Compatibility and requirements
------------------------------

GPP-Publicatiebank itself makes use of other services, APIs and software. The tables
below describe these dependencies.

PostgreSQL
**********

PostgreSQL is the database used. PostgreSQL 13 and newer are supported.

.. table:: PostgreSQL version support
   :widths: auto

   =============  ==========================
   PostgreSQL     Status
   =============  ==========================
   14             Supported
   15             Supported
   16             Automatically tested in CI
   =============  ==========================

Redis
*****

Redis is a key-value store used for caching purposes. Redis 5 and newer are supported.

.. table:: Redis version support
   :widths: auto

   =============  ==========================
   Redis          Status
   =============  ==========================
   5              Should work
   6              Automatically tested in CI
   7              Supported (tested via docker compose)
   =============  ==========================

Documenten API
**************

The Documenten API from the
`ZGW API's standard <https://vng-realisatie.github.io/gemma-zaken/>`_ is used to persist
the actual documents. Version 1.4 and newer are supported, since we use the large file
uploads mechanism.

.. seealso::

   The :ref:`installation requirements <installation_requirements>` list available
   Documenten API options.

.. table:: Documenten API version support
   :widths: auto

   ==============  ==========================
   Documenten API  Status
   ==============  ==========================
   1.4             Tested in CI (based on Open Zaak 1.16)
   1.5             Should work
   ==============  ==========================

.. note:: Version 1.1 - 1.3 mostly work, though you may see failures attempting to
   update the ``bronorganisatie`` if the ``publisher`` of a publication changes. This
   field was immutable before version 1.4.0 of the API specification.

GPP-zoeken
**********

GPP-zoeken manages the search index to facilitate full text and faceted search.

.. seealso::

    See the :ref:`configuration <configuration_services>` docs.

.. table:: GPP-zoeken API version support
   :widths: auto

   =============== ==========================
   GPP-zoeken API  Status
   =============== ==========================
   2.0.0-rc.0      Tested in CI
   =============== ==========================
