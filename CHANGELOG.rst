=============
Release notes
=============

Unreleased
==========

Upgrade procedure
-----------------

These points complement the "Configure a Catalogi API" step of the 3.0.0-rc.0 upgrade
procedure below.

* **Until the Catalogi API is configured, document uploads fail.** Direct uploads fail
  with an HTTP 500 error, uploads from a URL fail in the background task. Uploads for
  publications with an information category keep failing until the background
  synchronisation has created the informatieobjecttype of that category. Configure the
  Catalogi API right after deploying, or during a maintenance window.

* **Prepare Open Zaak** before or right after deploying:

    * The Catalogi API (ZTC) component must be enabled.
    * Give the application of GPP-publicatiebank the scopes ``catalogi.lezen`` and
      ``catalogi.schrijven``.
    * The informatieobjecttypen get new URLs in the catalogus of Open Zaak. Documents
      API authorisations that refer to the old
      ``.../catalogi/api/v1/informatieobjecttypen/...`` URLs of GPP-publicatiebank no
      longer apply. Once the Catalogi API is configured, authorise the new
      informatieobjecttypen. They are listed on the "View API resource URLs" page of the
      information categories. Also authorise the default informatieobjecttype from the
      global configuration, which has the confidentiality level ``vertrouwelijk``, so the
      maximum confidentiality level must be at least ``vertrouwelijk``. Applications
      with "heeft alle autorisaties" don't need this.

* [:issue:`526`] Instead of steps 1 and 2, you can run
  ``python src/manage.py setup_catalogi_api``. It creates the Catalogi API service from
  the Documents API service, with the same credentials, and runs the same setup as
  saving the global configuration. This only works with Open Zaak, and the organisation
  RSIN must be set.

* Afterwards, the ZTC service in Open Zaak that pointed to GPP-publicatiebank (see
  :issue:`394`) is no longer used and can be removed.

Features
--------

* [:issue:`526`] Added the ``setup_catalogi_api`` management command to set up the
  Catalogi API for an existing installation.
* [:issue:`501`] The inspection procedure list in the admin now links to the audit logs.

Documentation
-------------

* [:issue:`501`] Documented the Catalogi API: the required permissions, the service
  configuration and the global configuration fields.
* [:issue:`501`] Documented the inspection procedures and the new global configuration
  fields in the admin documentation.
* Fixed the commands to load the information categories and organisations in the
  installation instructions.

3.0.0-rc.0 (2026-10-12)
=======================

GPP-publicatiebank 3.0.0-rc.0 is a feature release that improves the reliability of
document uploads and adds inspection procedures ("inzageprocedures") to publications.

Upgrade procedure
-----------------

⚠️ We bumped the major version because of breaking changes in the API and because
upgrading requires manual actions. Read the breaking changes below before upgrading.
GPP-app is not affected by the API changes; other API clients should check their use of
``Document.eigenaar``.

* **Configure a Catalogi API directly after upgrading.** The informatieobjecttypen are
  no longer served by GPP-publicatiebank itself, but are managed in the Catalogi API of
  the Open Zaak instance that also provides the Documenten API. Until this is
  configured, new documents cannot be registered in the Documenten API, and existing
  documents there refer to informatieobjecttypen that no longer exist.

    1. In the admin, add a service of type Catalogi API (ZTC) for that Open Zaak
       instance.
    2. Open the global configuration. Make sure the organisation RSIN is set, select
       the new service as Catalogi API service and fill in the default reaction form
       URLs (see below). Leave the catalogus URL and default informatieobjecttype URL
       empty and save.
    3. GPP-publicatiebank creates a catalogus and a default informatieobjecttype in the
       Catalogi API. In the background, it then creates an informatieobjecttype for every
       information category and updates the informatieobjecttype of every existing
       document in the Documenten API. A Celery worker must be running for this.
    4. Check the information categories in the admin. If the synchronisation was
       interrupted, use the "Sync Document API" button to try again.

* **Run exactly one Celery beat process** (``/celery_beat.sh``). It schedules the
  periodic task that revokes publications when their inspection period has ended.
  Without it, the task silently doesn't run. See the installation documentation.

* The global configuration now requires the default reaction form URLs for
  "zienswijze" and "bezwaar". The first time you save them, existing inspection
  procedures without a reaction form URL are filled in.

* The database migrations change existing data:

    * Publications whose ``datum_einde_geldigheid`` is before their
      ``datum_begin_geldigheid`` get their ``datum_einde_geldigheid`` cleared.
    * The owner (``eigenaar``) is removed from documents. Documents now always have the
      owner of their publication; document owners that differed from the owner of the
      publication are not kept.

Breaking changes
----------------

* [:issue:`457`] ``Document.eigenaar`` is now read-only and always equals the owner of
  the publication. Values sent on create or update are ignored.
* [:issue:`457`] Removed the ``eigenaar`` filter from the documents list endpoint.
  Unknown query parameters are ignored, so clients that still use this filter receive
  unfiltered results.
* [:issue:`491`] Removed the built-in Catalogi API endpoint
  ``/catalogi/api/v1/informatieobjecttypen/{uuid}``. A Catalogi API (Open Zaak, the same
  instance as the Documenten API) is now required.
* [:issue:`458`] The API now rejects publications whose ``datumEindeGeldigheid`` is
  before their ``datumBeginGeldigheid``. This is also enforced by a database constraint.
* The API specification version is now 3.0.0. The endpoints remain available under the
  ``/api/v2`` URL prefix.

Features
--------

* You can now register an inspection procedure ("inzageprocedure") on a publication.

    - [:issue:`458`] Record the announcement URL, explanation, available legal remedy
      ("zienswijze" or "bezwaar"), reaction form URL and inspection period. Available
      in the admin (inline on the publication) and through the new
      ``/api/v2/inzageprocedure`` endpoint.
    - [:issue:`458`] The end of the inspection period is automatically moved to the
      next working day, taking Dutch public holidays into account.
    - [:issue:`458`] End dates can no longer be before start dates, for both inspection
      procedures and publications.
    - [:issue:`485`] Publications in the API include their inspection procedure
      (read-only).
    - [:issue:`459`] You can configure default reaction form URLs for "zienswijze" and
      "bezwaar" in the global configuration. When an inspection procedure has no
      reaction form URL, the default for its legal remedy is used.
    - [:issue:`460`] Publications can be revoked automatically when their inspection
      period ends ("automatisch intrekken"). A periodic task checks this daily.

* [:issue:`491`] Information categories now have a real informatieobjecttype in the
  Catalogi API. It is created automatically when an information category is created,
  and can be corrected manually in the admin.
* [:issue:`462`] You can now switch off the metadata stripping of documents in the
  global configuration. It remains switched on by default.
* [:issue:`456`] The publication list in the admin now shows the owner group.

Bugfixes
--------

* [:issue:`491`] Fixed document uploads failing under concurrent load. Open Zaak
  validated the informatieobjecttype by calling back into GPP-publicatiebank, while the
  web workers of GPP-publicatiebank were all waiting for Open Zaak. The uploads only
  failed after Open Zaak's 30 second timeout.
* [:issue:`451`] Fixed uploads of large documents failing because uploading a file part
  and unlocking the document used the generic 10 second service timeout. These calls
  now use ``DOCUMENTS_API_SLOW_OPERATIONS_TIMEOUT`` (default: 300 seconds). A higher
  timeout configured on the Documenten API service takes precedence.
* [:issue:`453`] Fixed Celery workers accumulating memory until they are killed. Pool
  child processes are now replaced after 50 tasks by default. Override this with
  ``CELERY_WORKER_MAX_TASKS_PER_CHILD``, and optionally set
  ``CELERY_WORKER_MAX_MEMORY_PER_CHILD`` (in KiB) as an additional limit.
* [:issue:`449`] Fixed uwsgi settings in the container start script that could not be
  overridden. You can now set ``UWSGI_PROCESSES``, ``UWSGI_THREADS``,
  ``UWSGI_HTTP_TIMEOUT``, ``UWSGI_HARAKIRI``, ``UWSGI_POST_BUFFERING`` and
  ``UWSGI_BUFFER_SIZE`` through the environment.
* [:issue:`457`] Fixed changes to the owner of a publication not being applied to its
  documents.
* [:issue:`461`] Alphabetical ordering in the API is now case-insensitive.

Project maintenance
-------------------

* [:issue:`466`] Added a performance test tool (Locust) with documentation.
* [:issue:`466`] Fixed the memory usage of the docker compose setup by limiting the
  number of open files.
* [:issue:`491`] Background tasks are retried with exponential backoff.
* Documented that a Celery beat process must be running.
* Upgraded dependencies to their latest (security) releases and dropped ``gitpython``.
* Stopped third-party link timeouts from failing the documentation CI.

2.1.0 (2026-04-22)
==================

The release candidate is now released as stable version.

Bugfixes
--------

* [:issue:`435`] Fixed MS Office files being corrupted by the metadata stripping.
* [:issue:`433`] Fixed the download endpoint for legacy documents created before
  the metadata stripping feature was introduced.
* Fixed broken asset references.

Project maintenance
-------------------

* Upgraded dependencies to their latest security releases.

2.1.0-rc.0 (2026-03-04)
=======================

GPP-publicatiebank 2.1.0-rc.0 is a feature release.

Upgrade procedure
-----------------

The metadata stripping is not automatically applied to existing documents already present
in GPP-publicatiebank. We've added a command line interface to perform this in bulk. In
short, this will check all existing documents that are not marked as "metadata stripped",
check if they can be stripped and if so, strip the metadata + upload the modified
documents to the document storage. Finally, the updated documents will be offered to
the search index for re-indexing.

.. note::

    In a Kubernetes pod or docker container, call the management command:

    .. code-block:: bash

      python src/manage.py strip_all_files --base-url https://publicatiebank.example.com

    The base URL is the root URL where your GPP-publicatiebank instance is hosted.

Features
--------

* You can now specify organisation units as "group owners" for publications.

    - [:issue:`369`] Define organisation units in the admin and expose them via the API.
    - [:issue:`370`] Support organisation units as publication owner in the admin and API.
    - [:issue:`371`] Added support for filtering publications in the API based on the
      owning group.
    - [:issue:`372`] Added bulk action in the admin to (re)assign the owner group of
      publications.

* The files added to the publications are now stripped of their internal metadata (on a
  best-effort basis).

    - [:issue:`386`] Added metadata stripping of PDF files.
    - [:issue:`388`] Added metadata stripping of "Open Document"-type documents (e.g.
      from LibreOffice and OpenOffice).
    - [:issue:`387`] Added metadata stripping of MS Office (2007+) files.
    - [:issue:`390`] Added metadata stripping of ZIP files.
    - [:issue:`391`] Added metadata stripping of HTML files.

* [:issue:`290`] The "organisations" fixture now includes additional value lists from
  overheid.nl:

    - Caribische openbare lichamen
    - Provincies
    - Waterschappen
    - zbo's

* [:issue:`290`] Existing organisations are updated based on the updated value lists
  versions, applying some corrections and additions.
* [:issue:`393`] Updated the branding (favicon + titles) with the GPP-Woo assets.
* [:issue:`167`] You can now filter documents in the API that are ready or not ready
  for publication, where ready is defined as "upload complete and metadata stripped
  if applicable".

Bugfixes
--------

* Fixed the API schema documenation for UUID-filter parameters that reported wrong
  parameter types.
* [:issue:`384`] Fixed phone number validation for API credential contact details being
  too strict.
* [:issue:`413`] Fixed documents retrieved from external Documents APIs not being queued
  for indexing to GPP-Zoeken.

Project maintenance
-------------------

* Upgraded dependencies to their latest security releases.
* Ignore npmjs links in the docs build, as they block bots now.
* Upgraded deprecated Github Actions to their latest versions.
* Upgraded dependencies to their latest versions, preparing for OTel integration.
* Updated uwsgi logs to not use the ``event`` key due to the associated high cardinality.
* [:issue:`399`] Upgrade to the latest Celery version.
* Documentation updates:

    - Added documentation for the automated publishing flow from external systems.
    - Added missing municipalities to financiers.
    - Updated the CVE link to the new CVE-website.

* Refactored some internal tooling to use more shared-library utilities.
* Removed optional and unused dependencies.
* Simplified the frontend build system by using esbuild.
* Optimized the memory usage of flower.

2.0.0 (2025-09-01)
==================

Major feature release - continue reading for the breaking changes.

Upgrade procedure
-----------------

⚠️ We bumped the major version because some of the changes are technically breaking
changes, which affect GPP-app and equivalent alternatives. GPP-burgerportaal should not
be affected. You will need GPP-app 3.x or newer.

No manual actions are needed.

Breaking changes
----------------

* Bumped the major version of the API to ``v2``. All the endpoints moved to the
  ``/api/v2`` URL prefix. We *also* still serve the endpoints under the ``/api/v1``
  prefix to make transitioning easier, but this is undocumented and deprecated. Most
  likely we'll remove this in the next feature release.

* The publication status field of the ``Publicatie`` and ``Document`` resource now has
  restrictions in the allowed state transitions. Before 2.0.0, you could change the
  ``publicatiestatus`` to any possible status, which now is no longer possible. The
  allowed state transitions are documented in the API specification.

* Removed ``documenthandelingen`` - the information can be extracted from the new date
  and datetime fields on ``Document``.

* Changed built-in group names - update your OpenID Connect role/group names accordingly.

    * ``Functioneel Beheer`` -> ``FunctioneelBeheer``
    * ``Technisch Beheer`` -> ``TechnischBeheer``

* The minimum required Documenten API version is raised from 1.1 to 1.4.

Features
--------

* [:issue:`361`] The new date fields ``gepubliceerd_op``, ``datum_begin_geldigheid``
  and ``datum_einde_geldigheid`` are now also sent to the search index for indexing.
* [:issue:`349`] When the ``publisher`` changes on a publication, the ``bronorganisatie`` in the underlying
  Documents API storage is now updated for the documents belonging to the publication.
* [:issue:`367`] The admin panel UI for related documents within a publication is simplified.
* [:issue:`364`, :issue:`365` :issue:`366`] Improved the field organization for publications, documents and topics in the admin.
* [:issue:`363`] The deprecated `identifier` field is no longer displayed in the document list in the admin.
* [:issue:`295`] You can now update ``Document.creatiedatum`` via the API.
* [:issue:`266`] The ``Publicatie`` and ``Document`` publication status progressions now have a
  well-documented life cycle. The API validates that these status changes are
  meaningfull.
* [:issue:`214`, :issue:`215`] You can now configure a pattern for the URLs to a publication in the
  internal application (GPP-app) and public citizen portal (GPP-burgerportaal). These
  URLs are included in the API responses for publications.
* [:issue:`275`] You can now add (custom) descriptions to information categories in the
  metadata loaded from overheid.nl value lists.
* [:issue:`270`] You can now add the RSIN to organisations in the metadata loaded from
  overheid.nl value lists.
* [:issue:`194`] You can now add (additional) ``identifiers`` ("kenmerken") to documents. Any
  specified identifiers are also indexed in GPP-zoeken.
* [:issue:`195`] You can now add (additional) ``identifiers`` ("kenmerken") to publications. Any
  specified identifiers are also indexed in GPP-zoeken.
* [:issue:`263`] Added support for "concept" publications with incomplete data. The validation
  requirements are relaxed since a lot of information may be unknown in automated
  publishing architectures. The validation is enforced when the publication status
  changes from ``concept``.
* [:issue:`304`] You can now delete documents via the API. The delete cascades to the underlying
  Documenten API and destroys the metadata and content there.
* [:issue:`282`] Added new metadata date/datetime fields:

    * Publication: published on, revoked on, start date, end date.
    * Document: received on, signed on, published on, revoked on.

* [:issue:`320`] Changed the built-in user group names to remove spaces, for better
  compatibility with role names in MS Entra.
* [:issue:`283`] The archiving parameters are now calculated when a publication is published
  rather than when it's created.
* [:issue:`272`] Update the value for ``auteur`` in the Documenten API for documents that we
  register.
* [:issue:`319`] Support filtering in the API on identifiers ("kenmerken", value and/or source).
* [:issue:`274`] API clients can now provide a link to a resource in a Documents API instead of
  uploading the metadata and file parts content.
* [:issue:`271`] The RSIN of the related publisher (organisation) is now used when the document
  metadata is registered in the Documents API. If none is available, the global default
  is used as was the situation before.


Bugfixes
--------

* [:issue:`307`, :issue:`311`] Fixed container restarts overwriting custom archiving parameters set on
  information categories.
* [:issue:`298`] Fixed changes to ``publisher`` and/or ``informatieCategorieen`` on a
  publication not triggering document re-indexing for the related documents.
* [:issue:`330`] Revoked publications are now excluded from the choices in the admin when
  adding a document.
* [:issue:`309`] Fixed not always deleting the document from the Documents API when a document
  is deleted from GPP-publicatiebank.

Project maintenance
-------------------

* Replaced the CI pipeline for quality control on the OpenAPI specification with a
  reusable variant.
* Updated frontend dependencies (security fixes).
* Replaced boilerplate utilities with their equivalents from maykin-common.
* Upgraded external packages to their latest (security) releases.
* Removed the unused Javascript toolchain.
* Updated github issue templates.
* [:issue:`292`] Removed ``documenthandelingen``.
* [:issue:`340`] Deprecated ``identifier`` on the ``Document`` resource, use ``kenmerken``
  instead.
* Application logs are now structured (JSON) using ``structlog``.
* Updated project documentation.

2.0.0-rc.0 (2025-07-16)
=======================

GPP-publicatiebank 2.0.0-rc.0 is a feature release.

Upgrade procedure
-----------------

⚠️ We bumped the major version because some of the changes are technically breaking
changes, which affect GPP-app and equivalent alternatives. GPP-burgerportaal should not
be affected. You will need GPP-app 3.x or newer.

No manual actions are needed.

Breaking changes
----------------

* Bumped the major version of the API to ``v2``. All the endpoints moved to the
  ``/api/v2`` URL prefix. We *also* still serve the endpoints under the ``/api/v1``
  prefix to make transitioning easier, but this is undocumented and deprecated. Most
  likely we'll remove this in the next feature release.

* The publication status field of the ``Publicatie`` and ``Document`` resource now has
  restrictions in the allowed state transitions. Before 2.0.0, you could change the
  ``publicatiestatus`` to any possible status, which now is no longer possible. The
  allowed state transitions are documented in the API specification.

* Removed ``documenthandelingen`` - the information can be extracted from the new date
  and datetime fields on ``Document``.

* Changed built-in group names - update your OpenID Connect role/group names accordingly.

    * ``Functioneel Beheer`` -> ``FunctioneelBeheer``
    * ``Technisch Beheer`` -> ``TechnischBeheer``

Features
--------

* [:issue:`295`] You can now update ``Document.creatiedatum`` via the API.
* [:issue:`266`] The ``Publicatie`` and ``Document`` publication status progressions now have a
  well-documented life cycle. The API validates that these status changes are
  meaningfull.
* [:issue:`214`, :issue:`215`] You can now configure a pattern for the URLs to a publication in the
  internal application (GPP-app) and public citizen portal (GPP-burgerportaal). These
  URLs are included in the API responses for publications.
* [:issue:`275`] You can now add (custom) descriptions to information categories in the
  metadata loaded from overheid.nl value lists.
* [:issue:`270`] You can now add the RSIN to organisations in the metadata loaded from
  overheid.nl value lists.
* [:issue:`194`] You can now add (additional) ``identifiers`` ("kenmerken") to documents. Any
  specified identifiers are also indexed in GPP-zoeken.
* [:issue:`195`] You can now add (additional) ``identifiers`` ("kenmerken") to publications. Any
  specified identifiers are also indexed in GPP-zoeken.
* [:issue:`263`] Added support for "concept" publications with incomplete data. The validation
  requirements are relaxed since a lot of information may be unknown in automated
  publishing architectures. The validation is enforced when the publication status
  changes from ``concept``.
* [:issue:`304`] You can now delete documents via the API. The delete cascades to the underlying
  Documenten API and destroys the metadata and content there.
* [:issue:`282`] Added new metadata date/datetime fields:

    * Publication: published on, revoked on, start date, end date.
    * Document: received on, signed on, published on, revoked on.

* [:issue:`320`] Changed the built-in user group names to remove spaces, for better
  compatibility with role names in MS Entra.
* [:issue:`283`] The archiving parameters are now calculated when a publication is published
  rather than when it's created.
* [:issue:`272`] Update the value for ``auteur`` in the Documenten API for documents that we
  register.
* [:issue:`319`] Support filtering in the API on identifiers ("kenmerken", value and/or source).
* [:issue:`274`] API clients can now provide a link to a resource in a Documents API instead of
  uploading the metadata and file parts content.
* [:issue:`271`] The RSIN of the related publisher (organisation) is now used when the document
  metadata is registered in the Documents API. If none is available, the global default
  is used as was the situation before.

Bugfixes
--------

* [:issue:`307`, :issue:`311`] Fixed container restarts overwriting custom archiving parameters set on
  information categories.
* [:issue:`298`] Fixed changes to ``publisher`` and/or ``informatieCategorieen`` on a
  publication not triggering document re-indexing for the related documents.
* [:issue:`330`] Revoked publications are now excluded from the choices in the admin when
  adding a document.
* [:issue:`309`] Fixed not always deleting the document from the Documents API when a document
  is deleted from GPP-publicatiebank.

Project maintenance
-------------------

* Replaced the CI pipeline for quality control on the OpenAPI specification with a
  reusable variant.
* Updated frontend dependencies (security fixes).
* Replaced boilerplate utilities with their equivalents from maykin-common.
* Upgraded external packages to their latest (security) releases.
* Removed the unused Javascript toolchain.
* Updated github issue templates.
* [:issue:`292`] Removed ``documenthandelingen``.
* [:issue:`340`] Deprecated ``identifier`` on the ``Document`` resource, use ``kenmerken``
  instead.
* Application logs are now structured (JSON) using ``structlog``.
* Updated project documentation.

1.2.0 (2025-07-14)
==================

Stable feature release - there are no changes compared to the release candidate.

Upgrade procedure
-----------------

* ⚠️ PostgreSQL 13 is no longer supported due to our framework dropping support for it.
  Upgrading to newer Postgres versions should be straight forward.

* GPP-publicatiebank instances now need a persistent volume for the topic image uploads.
  Our Helm charts have been updated, and more information is available in the Helm
  installation documentation.

Features
--------

* [:issue:`205`, :issue:`206`, :issue:`207`, :issue:`209`, :issue:`211`, :issue:`237`]
  Added "Topics" to group multiple publications together:

    * Topics are used to bundle publications together that have social relevance.
    * They support images and promotion on the citizen portal.
    * Topics are also indexed in GPP-zoeken.

* [:issue:`232`] The large file uploads (in particular with multiple chunks) are now optimized
  to consume much less memory.
* [:issue:`235`] The API now supports filtering on multiple publication statuses at the same time.
* [:issue:`198`, :issue:`199`, :issue:`200`, :issue:`201`, :issue:`202`, :issue:`203`, :issue:`204`]
  Added support for archive parameters and retention policies:

    * The retention policy can be specified on information categories.
    * The archive action date of publications is automatically calculated.
    * You can manually override these parameters if needed.
    * Relevant filters on API endpoints have been added.
    * Added bulk actions in the admin to reassess the retention policy.

* [:issue:`51`] Added bulk revocation actions in the admin for publications and documents.
* [:issue:`260`] You can now reassign the owner of a publication/document (both via the API and
  the admin interface).

Bugfixes
--------

* Fixed misconfiguration of our docker compose file.
* [:issue:`252`] Fixed invalid format of some translations.

Project maintenance
-------------------

* Updated the documentation.
* Switched code quality tools to Ruff.
* Simplified documentation test tools.
* Added upgrade-check mechanism for "hard stops".
* [:issue:`277`] Upgraded framework version to next LTS release.

1.2.0-rc.0 (2025-05-29)
=======================

Feature release.

Upgrade procedure
-----------------

* ⚠️ PostgreSQL 13 is no longer supported due to our framework dropping support for it.
  Upgrading to newer Postgres versions should be straight forward.

* GPP-publicatiebank instances now need a persistent volume for the topic image uploads.
  Our Helm charts have been updated, and more information is available in the Helm
  installation documentation.

Features
--------

* [:issue:`205`, :issue:`206`, :issue:`207`, :issue:`209`, :issue:`211`, :issue:`237`]
  Added "Topics" to group multiple publications together:

    * Topics are used to bundle publications together that have social relevance.
    * They support images and promotion on the citizen portal.
    * Topics are also indexed in GPP-zoeken.

* [:issue:`232`] The large file uploads (in particular with multiple chunks) are now optimized
  to consume much less memory.
* [:issue:`235`] The API now supports filtering on multiple publication statuses at the same time.
* [:issue:`198`, :issue:`199`, :issue:`200`, :issue:`201`, :issue:`202`, :issue:`203`, :issue:`204`]
  Added support for archive parameters and retention policies:

    * The retention policy can be specified on information categories.
    * The archive action date of publications is automatically calculated.
    * You can manually override these parameters if needed.
    * Relevant filters on API endpoints have been added.
    * Added bulk actions in the admin to reassess the retention policy.

* [:issue:`51`] Added bulk revocation actions in the admin for publications and documents.
* [:issue:`260`] You can now reassign the owner of a publication/document (both via the API and
  the admin interface).

Bugfixes
--------

* Fixed misconfiguration of our docker compose file.
* [:issue:`252`] Fixed invalid format of some translations.

Project maintenance
-------------------

* Updated the documentation.
* Switched code quality tools to Ruff.
* Simplified documentation test tools.
* Added upgrade-check mechanism for "hard stops".
* [:issue:`277`] Upgraded framework version to next LTS release.

1.1.1 (2025-05-02)
==================

Bugfix release.

* [:issue:`267`] Added missing "documenthandeling" TOOI identifier, required for valid sitemap
  generation.

1.1.0 (2025-04-16)
==================

Feature release to integrate with GPP-zoeken.

GPP-zoeken manages the search index for the citizen portal. While it's technically an
optional component for GPP-publicatiebank, we recommend making use of it in all cases
for the best user experience for your users.

Features
--------

* GPP-publicatiebank now dispatches publication status changes to GPP-zoeken to make
  publications and/or documents available to the search index (or revoke them).
* Added bulk index/index-removal actions in the admin for publications and documents.
* The document upload status to the backing Documenten API is now tracked.

Project maintenance
-------------------

* Updated documentation for GPP-zoeken integration.

1.1.0-rc.2 (2025-04-14)
=======================

Third 1.1 release candidate.

* [:issue:`244`] Fixed incomplete bulk delete fix.

1.1.0-rc.1 (2025-04-10)
=======================

Second 1.1 release candidate.

* [:issue:`244`] Fixed bulk delete not triggering index removal in GPP-zoeken.

1.1.0-rc.0 (2025-03-26)
=======================

* Updated the documentation to describe new features.
* Fixed broken API spec link in the documentation.

1.1.0-beta.0 (2025-03-12)
=========================

* We now track whether the document file uploads have completed or not.
* Added GPP-Zoeken integration (opt-in). To opt in, you must configure the appropriate
  service to use and update your infrastructure to deploy the celery containers to
  process background tasks.

1.0.0-rc.0 (2024-12-12)
=======================

We proudly announce the first release candidate of GPP-Publicatiebank!

The 1.0 version of this component is ready for production. It provides the minimal
functionalities to be able to comply with the WOO legislation in your organization.

Features
--------

* Admin panel for technical and functional administrators

    - Manage metadata for publications, such as organizations, information categories
      and themes.
    - Manage publications and documents, where a publication acts as a container for one
      or more documents.
    - Manage API clients and user accounts.
    - View (audit) logs for actions performed on/related to publications.
    - Configure connections to external services, like a Documents API and OpenID
      Connect provider.

* JSON API for full publication life-cycle management.
* Automatically populated metadata from national value lists sourced from overheid.nl.
* OpenID Connect or local user account with MFA authentication options for the admin
  panel.
* Extensive documentation, from API specification to (admin) user manual.
* Helm charts to deploy on Kubernetes cluster(s).
