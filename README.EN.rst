=============================
Public documents registration
=============================

:Version: 2.0.0
:Source: https://github.com/GPP-Woo/GPP-publicatiebank
:Keywords: WOO, Public Documents, NL, Open Data

|docs| |docker|

A registration providing the functionalities for a "public documents" storage.

(`Nederlandse versie`_)

Developed by `Maykin B.V.`_ for ICATT and Dimpact.

Introduction
============

In the Netherlands, legislation require governments to act from the principles of
Openness (`Wet Open Overheid (Dutch) <https://www.rijksoverheid.nl/onderwerpen/wet-open-overheid-woo>`_). Government organizations are required - by law - to actively
publish documents produced for the Public sphere, making them accessible to interested
parties/citizens. Dimpact provides a Generic Publication Platform to facilitate this for
municipalities, of which the Public Documents Registration component is one part.

This registration component makes it possible to draft, manage and publish publications.
It exposes the publications, attached documents and supporting resource belonging to
publications, such as:

* organisations (municipalities, working groups)
* reference value lists (file formats, information categories, themes...)
* publications and associated documents
* metadata models and expected shapes of metadata

The component interfaces with a GPP-zoeken and ensures the metadata and content
of documents is indexed, enabling the citizen portal to search through the publications.
The data is provided in a format making it suitable to be indexed by the national
crawler, by complying with the
`Woo-Metadata-standard (Dutch) <https://standaarden.overheid.nl/diwoo/metadata>`_.

API specification
=================

|oas|

==============  ==============  =============================
Version         Release date    API specification
==============  ==============  =============================
latest          n/a             `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/main/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/main/src/woo_publications/api/openapi.yaml>`_,
                                (`changes <https://github.com/GPP-Woo/GPP-publicatiebank/compare/2.0.0..main>`_)
2.0.0           2025-07-16      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/2.0.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/2.0.0/src/woo_publications/api/openapi.yaml>`_,
                                (`changes <https://github.com/GPP-Woo/GPP-publicatiebank/compare/1.2.0..2.0.0>`_)
1.1.0           2025-05-19      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.2.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.2.0/src/woo_publications/api/openapi.yaml>`_,
                                (`changes <https://github.com/GPP-Woo/GPP-publicatiebank/compare/1.0.0-rc.0..1.2.0>`_)
1.0.0           2024-12-12      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.0.0-rc.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.0.0-rc.0/src/woo_publications/api/openapi.yaml>`_
==============  ==============  =============================

See: `All versions and changes <https://github.com/GPP-Woo/GPP-publicatiebank/blob/main/CHANGELOG.rst>`_


Developers
==========

|build-status| |coverage| |ruff| |docker| |python-versions|

This repository contains the source code for the registration component. To quickly
get started, we recommend using the Docker image. You can also build the
project from the source code. For this, please look at `INSTALL.rst <INSTALL.rst>`_.

Quickstart
----------

1. Download and run woo-publications:

   .. code:: bash

      wget https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/main/docker-compose.yml
      docker-compose up -d --no-build

2. In the browser, navigate to ``http://localhost:8000/`` to access the admin
   and the API. You can log in with the ``admin`` / ``admin`` credentials.


References
==========

* `Documentation <https://gpp-publicatiebank.readthedocs.io>`_
* `Docker image <https://github.com/GPP-Woo/GPP-publicatiebank/pkgs/container/gpp-publicatiebank>`_
* `Issues <https://github.com/GPP-Woo/GPP-publicatiebank/issues>`_
* `Code <https://github.com/GPP-Woo/GPP-publicatiebank>`_
* `Community <https://github.com/GPP-Woo>`_


License
=======

Copyright © Maykin 2024

Licensed under the EUPL_


.. _`Nederlandse versie`: README.rst

.. _`Maykin B.V.`: https://www.maykinmedia.nl

.. _`EUPL`: LICENSE.md

.. |build-status| image:: https://github.com/GPP-Woo/GPP-publicatiebank/actions/workflows/ci.yml/badge.svg
    :alt: Build status
    :target: https://github.com/GPP-Woo/GPP-publicatiebank/actions/workflows/ci.yml

.. |docs| image:: https://readthedocs.org/projects/gpp-publicatiebank/badge/?version=latest
    :target: https://gpp-publicatiebank.readthedocs.io/
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/GPP-Woo/GPP-publicatiebank/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage
    :target: https://codecov.io/gh/GPP-Woo/GPP-publicatiebank

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Ruff

.. |docker| image:: https://img.shields.io/docker/v/maykinmedia/woo-publications?sort=semver
    :alt: Docker image
    :target: https://hub.docker.com/r/maykinmedia/woo-publications

.. |python-versions| image:: https://img.shields.io/badge/python-3.12%2B-blue.svg
    :alt: Supported Python version

.. |oas| image:: https://github.com/GPP-Woo/GPP-publicatiebank/actions/workflows/oas.yml/badge.svg
    :alt: OpenAPI specification checks
    :target: https://github.com/GPP-Woo/GPP-publicatiebank/actions/workflows/oas.yml
