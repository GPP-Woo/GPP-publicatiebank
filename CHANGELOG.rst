=============
Release notes
=============

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
