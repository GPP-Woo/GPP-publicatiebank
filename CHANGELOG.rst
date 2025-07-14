=============
Release notes
=============

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

* [#205, #206, #207, #209, #211, #237] Added "Topics" to group multiple publications together:

    * Topics are used to bundle publications together that have social relevance.
    * They support images and promotion on the citizen portal.
    * Topics are also indexed in GPP-zoeken.

* [#232] The large file uploads (in particular with multiple chunks) are now optimized
  to consume much less memory.
* [#235] The API now supports filtering on multiple publication statuses at the same time.
* [#198, #199, #200, #201, #202, #203, #204] Added support for archive parameters and retention policies:

    * The retention policy can be specified on information categories.
    * The archive action date of publications is automatically calculated.
    * You can manually override these parameters if needed.
    * Relevant filters on API endpoints have been added.
    * Added bulk actions in the admin to reassess the retention policy.

* [#51] Added bulk revocation actions in the admin for publications and documents.
* [#260] You can now reassign the owner of a publication/document (both via the API and
  the admin interface).

Bugfixes
--------

* Fixed misconfiguration of our docker compose file.
* [#252] Fixed invalid format of some translations.

Project maintenance
-------------------

* Updated the documentation.
* Switched code quality tools to Ruff.
* Simplified documentation test tools.
* Added upgrade-check mechanism for "hard stops".
* [#277] Upgraded framework version to next LTS release.

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

* [#205, #206, #207, #209, #211, #237] Added "Topics" to group multiple publications together:

    * Topics are used to bundle publications together that have social relevance.
    * They support images and promotion on the citizen portal.
    * Topics are also indexed in GPP-zoeken.

* [#232] The large file uploads (in particular with multiple chunks) are now optimized
  to consume much less memory.
* [#235] The API now supports filtering on multiple publication statuses at the same time.
* [#198, #199, #200, #201, #202, #203, #204] Added support for archive parameters and retention policies:

    * The retention policy can be specified on information categories.
    * The archive action date of publications is automatically calculated.
    * You can manually override these parameters if needed.
    * Relevant filters on API endpoints have been added.
    * Added bulk actions in the admin to reassess the retention policy.

* [#51] Added bulk revocation actions in the admin for publications and documents.
* [#260] You can now reassign the owner of a publication/document (both via the API and
  the admin interface).

Bugfixes
--------

* Fixed misconfiguration of our docker compose file.
* [#252] Fixed invalid format of some translations.

Project maintenance
-------------------

* Updated the documentation.
* Switched code quality tools to Ruff.
* Simplified documentation test tools.
* Added upgrade-check mechanism for "hard stops".
* [#277] Upgraded framework version to next LTS release.

1.1.1 (2025-05-02)
==================

Bugfix release.

* [#267] Added missing "documenthandeling" TOOI identifier, required for valid sitemap
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

* [#244] Fixed incomplete bulk delete fix.

1.1.0-rc.1 (2025-04-10)
=======================

Second 1.1 release candidate.

* [#244] Fixed bulk delete not triggering index removal in GPP-zoeken.

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
