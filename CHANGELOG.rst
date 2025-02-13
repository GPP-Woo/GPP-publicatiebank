=============
Release notes
=============

dev (UNRELEASED)
================

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
    - Manage API clients and user acocunts.
    - View (audit) logs for actions performed on/related to publications.
    - Configure connections to external services, like a Documents API and OpenID
      Connect provider.

* JSON API for full publication life-cycle management.
* Automatically populated metadata from national value lists sourced from overheid.nl.
* OpenID Connect or local user account with MFA authentication options for the admin
  panel.
* Extensive documentation, from API specification to (admin) user manual.
* Helm charts to deploy on Kubernetes cluster(s).
