===============================
Openbare Documenten Registratie
===============================

:Version: 2.0.0
:Source: https://github.com/GPP-Woo/GPP-publicatiebank
:Keywords: WOO, Openbare Documenten, NL, Open Data

|docs| |docker|

Een registratie die voorziet in de "Openbare Documenten opslag"-functionaliteiten.

(`English version`_)

Ontwikkeld door `Maykin B.V.`_ in opdracht ICATT en Dimpact.

Introductie
===========

De `Wet Open Overheid <https://www.rijksoverheid.nl/onderwerpen/wet-open-overheid-woo>`_
vereist dat overheidsorganisaties actief documenten openbaar maken zodat deze door
geïnteresseerde partijen ingezien kunnen worden. Dimpact voorziet in een Generiek
Publicatieplatform om dit mogelijk te maken voor gemeenten, waarvan de openbare
documentenregistratiecomponent een onderdeel vormt.

Dit registratiecomponent laat het publicatiecomponent toe om publicaties (van documenten
) aan te maken, beheren en op te vragen en ontsluit ondersteunende entiteiten die bij
een publicatie horen, zoals:

* organisaties (gemeenten, samenwerkingsverbanden)
* waardenlijsten (bestandsformaten, informatiecategorieën, thema's...)
* publicaties en bijhorende documenten
* metamodellen/metagegevens

Het component koppelt met de GPP-zoeken en zorgt dat de metagegevens en inhoud van
documenten geïndexeerd worden zodat het burgerportaal deze kan doorzoeken. De gegevens
worden aangeboden in een formaat zodat deze aan de
`Woo-Metadata-standaard <https://standaarden.overheid.nl/diwoo/metadata>`_ voldoen.

API specificatie
================

|oas|

==============  ==============  =============================
Versie          Release datum   API specificatie
==============  ==============  =============================
latest          n/a             `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/main/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/main/src/woo_publications/api/openapi.yaml>`_,
                                (`verschillen <https://github.com/GPP-Woo/GPP-publicatiebank/compare/2.0.0..main>`_)
2.0.0           2025-07-16      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/2.0.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/2.0.0/src/woo_publications/api/openapi.yaml>`_,
                                (`verschillen <https://github.com/GPP-Woo/GPP-publicatiebank/compare/1.2.0..2.0.0>`_)
1.1.0           2025-05-19      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.2.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.2.0/src/woo_publications/api/openapi.yaml>`_,
                                (`verschillen <https://github.com/GPP-Woo/GPP-publicatiebank/compare/1.0.0-rc.0..1.2.0>`_)
1.0.0           2024-12-12      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.0.0-rc.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/1.0.0-rc.0/src/woo_publications/api/openapi.yaml>`_
==============  ==============  =============================

Zie: `Alle versies en wijzigingen <https://github.com/GPP-Woo/GPP-publicatiebank/blob/main/CHANGELOG.rst>`_


Ontwikkelaars
=============

|build-status| |coverage| |ruff| |docker| |python-versions|

Deze repository bevat de broncode voor het registratiecomponent. Om snel aan de slag
te gaan, raden we aan om de Docker image te gebruiken. Uiteraard kan je ook
het project zelf bouwen van de broncode. Zie hiervoor `INSTALL.rst <INSTALL.rst>`_.

Quickstart
----------

1. Download en start woo-publications:

   .. code:: bash

      wget https://raw.githubusercontent.com/GPP-Woo/GPP-publicatiebank/main/docker-compose.yml
      docker-compose up -d --no-build

2. In de browser, navigeer naar ``http://localhost:8000/`` om de beheerinterface
   en de API te benaderen, waar je kan inloggen met ``admin`` / ``admin``.


Links
=====

* `Documentatie <https://gpp-publicatiebank.readthedocs.io>`_
* `Docker image <https://github.com/GPP-Woo/GPP-publicatiebank/pkgs/container/gpp-publicatiebank>`_
* `Issues <https://github.com/GPP-Woo/GPP-publicatiebank/issues>`_
* `Code <https://github.com/GPP-Woo/GPP-publicatiebank>`_
* `Community <https://github.com/GPP-Woo>`_


Licentie
========

Copyright © Maykin 2024

Licensed under the EUPL_


.. _`English version`: README.EN.rst

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
