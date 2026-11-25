.. _installation_docker_compose:

Install using Docker Compose
============================

This installation is meant for people who want to just try out WOO Publications on
their own machine.

A `Docker Compose`_ file is available to get the app up and running in minutes.
It contains 'convenience' settings, which means that no additional
configuration is needed to run the app. Therefore, it should **not** be used
for anything other than testing. For example, it includes:

* A default ``SECRET_KEY`` environment variable
* A predefined database with the environment variable
  ``POSTGRES_HOST_AUTH_METHOD=trust``. This lets us connect to the database
  without using a password.
* Debug mode is enabled.
* Admin superuser credentials (``admin`` / ``admin``).
* An API key ``insecure-ea1a8d297e3b2d3313b8a30b18959c3``.

Besides GPP-publicatiebank (``web``, ``celery``, ``celery-beat`` and ``celery-flower``),
the stack contains a PostgreSQL database, Redis, Open Zaak (which provides the Documents
API and the Catalogi API) and the GPP-zoeken API. Elasticsearch is not configured in
this dev stack.

.. _`WSL`: https://docs.microsoft.com/en-us/windows/wsl/

Prerequisites
-------------

You will only need Docker tooling and nothing more:

* `Docker Engine`_ (Desktop or Server)
* `Docker Compose`_ (sometimes comes bundled with Docker Engine)

.. _`Docker Engine`: https://docs.docker.com/engine/install/
.. _`Docker Compose`: https://docs.docker.com/compose/install/


Getting started
---------------

1. Download the project as ZIP-file:

   .. code:: bash

      wget https://github.com/GPP-Woo/GPP-publicatiebank/archive/refs/heads/main.zip
      unzip main.zip
      cd GPP-publicatiebank-main

2. Start the docker containers with ``docker compose``. If you want to run the
   containers in the background, add the ``-d`` option to the command below:

   .. code:: bash

      docker compose up


   Docker creates the network, the volumes and the containers of the stack and then
   shows their logs. The first start takes a while, because the images are downloaded
   and the database migrations are applied.

3. Navigate to ``http://127.0.0.1:8000/admin/``, where you can log in with the
   ``admin`` username and ``admin`` password.

4. Configure the services. Since version 3.0.0, document uploads fail until the Catalogi
   API is set up. The fixtures only provide the Documents API service, and the global
   configuration can only be saved when all three services are selected.

   a. In the admin, navigate to **Configuratie** > **Services** and add two services
      (label and slug of your choice):

      * Catalogi API: type "ZTC (Zaaktypen)", API root
        ``http://openzaak.docker.internal:8001/catalogi/api/v1/``, authorization type
        "ZGW client_id + secret", client ID ``woo-publications-dev`` and secret
        ``insecure-yQL9Rzh4eHGVmYx5w3J2gu`` (the same credentials as the Documents API
        service).
      * GPP-zoeken: type "ORC (Overige)", API root
        ``http://gpp-zoeken-web:8000/api/v1/``, authorization type "API key", header key
        ``Authorization`` and header value ``Token insecure-RySD8u5xkb9PH6AJtaZV4Y``.

   b. Navigate to **Configuratie** > **Algemene instellingen**, select the three
      services, fill in the ``RSIN organisatie`` and the default reaction form URLs
      (``Reactieformulier-URL zienswijze`` and ``Reactieformulier-URL bezwaar``) and
      save. Saving creates the catalogus and the default informatieobjecttype. The
      information categories get their informatieobjecttype in the background.

      .. note:: The Open Zaak instance of the stack already has a catalogus for RSIN
         ``100000198``. If you use this RSIN, also fill in the ``Catalogus-URL``
         ``http://openzaak.docker.internal:8001/catalogi/api/v1/catalogussen/770dcb62-2469-4353-a2a7-e619df7e061f``.

   See :ref:`configuration_services_catalogi_api` for more details.

5. You can authenticate to the API endpoints with the
   ``Authorization: Token insecure-ea1a8d297e3b2d3313b8a30b18959c3`` HTTP request header.

6. To stop the containers, press *CTRL-C* or if you used the ``-d`` option:

   .. code:: bash

      docker compose stop

7. If you want to get newer versions, you need to ``pull`` because the
   ``docker-compose.yml`` contains no explicit versions:

   .. code:: bash

      docker compose pull
