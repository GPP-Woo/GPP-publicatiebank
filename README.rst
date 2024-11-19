===============================
Openbare Documenten Registratie
===============================

:Version: 0.1.0
:Source: https://github.com/GeneriekPublicatiePlatformWoo/registratie-component
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

Het component koppelt met de zoekindex (TODO) en zorgt dat de metagegevens en inhoud van
documenten geïndexeerd worden zodat het burgerportaal deze kan doorzoeken. De gegevens
worden aangeboden in een formaat zodat deze aan de
`Woo-Metadata-standaard <https://standaarden.overheid.nl/diwoo/metadata>`_ voldoen.

API specificatie
================

|oas|

==============  ==============  =============================
Versie          Release datum   API specificatie
==============  ==============  =============================
latest          n/a             `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GeneriekPublicatiePlatformWoo/registratie-component/main/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GeneriekPublicatiePlatformWoo/registratie-component/main/src/woo_publications/api/openapi.yaml>`_,
                                (`verschillen <https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/compare/0.1.0..main#diff-b9c28fec6c3f3fa5cff870d24601d6ab7027520f3b084cc767aefd258cb8c40a>`_)
0.1.0           YYYY-MM-DD      `ReDoc <https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/GeneriekPublicatiePlatformWoo/registratie-component/0.1.0/src/woo_publications/api/openapi.yaml>`_,
                                `Swagger <https://petstore.swagger.io/?url=https://raw.githubusercontent.com/GeneriekPublicatiePlatformWoo/registratie-component/0.1.0/src/woo_publications/api/openapi.yaml>`_
==============  ==============  =============================

Zie: `Alle versies en wijzigingen <https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/blob/main/CHANGELOG.rst>`_


Ontwikkelaars
=============

|build-status| |coverage| |black| |docker| |python-versions|

Deze repository bevat de broncode voor het registratiecomponent. Om snel aan de slag
te gaan, raden we aan om de Docker image te gebruiken. Uiteraard kan je ook
het project zelf bouwen van de broncode. Zie hiervoor `INSTALL.rst <INSTALL.rst>`_.

Quickstart
----------

1. Download en start woo-publications:

   .. code:: bash

      wget https://raw.githubusercontent.com/GeneriekPublicatiePlatformWoo/registratie-component/main/docker-compose.yml
      docker-compose up -d --no-build

2. In de browser, navigeer naar ``http://localhost:8000/`` om de beheerinterface
   en de API te benaderen, waar je kan inloggen met ``admin`` / ``admin``.


Links
=====

* `Documentatie <https://odrc.readthedocs.io>`_
* `Docker image <https://hub.docker.com/r/GeneriekPublicatiePlatformWoo/registratie-component>`_
* `Issues <https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/issues>`_
* `Code <https://github.com/GeneriekPublicatiePlatformWoo/registratie-component>`_
* `Community <https://github.com/GeneriekPublicatiePlatformWoo>`_


Licentie
========

Copyright © Maykin 2024

Licensed under the EUPL_


.. _`English version`: README.EN.rst

.. _`Maykin B.V.`: https://www.maykinmedia.nl

.. _`EUPL`: LICENSE.md

.. |build-status| image:: https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/actions/workflows/ci.yml/badge.svg
    :alt: Build status
    :target: https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/actions/workflows/ci.yml

.. |docs| image:: https://readthedocs.org/projects/odrc/badge/?version=latest
    :target: https://odrc.readthedocs.io/
    :alt: Documentation Status

.. |coverage| image:: https://codecov.io/github/GeneriekPublicatiePlatformWoo/registratie-component/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage
    :target: https://codecov.io/gh/GeneriekPublicatiePlatformWoo/registratie-component

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style
    :target: https://github.com/psf/black

.. |docker| image:: https://img.shields.io/docker/v/maykinmedia/woo-publications-api?sort=semver
    :alt: Docker image
    :target: https://hub.docker.com/r/maykinmedia/woo-publications-api

.. |python-versions| image:: https://img.shields.io/badge/python-3.12%2B-blue.svg
    :alt: Supported Python version

.. |oas| image:: https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/actions/workflows/oas.yml/badge.svg
    :alt: OpenAPI specification checks
    :target: https://github.com/GeneriekPublicatiePlatformWoo/registratie-component/actions/workflows/oas.yml
