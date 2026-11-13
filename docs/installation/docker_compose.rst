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
API and the Catalogi API) and GPP-zoeken with Elasticsearch.

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

4. Set up the Catalogi API. Since version 3.0.0, document uploads fail until this is
   done:

   a. In the admin, navigate to **Configuratie** > **Algemene instellingen**, fill in
      the ``RSIN organisatie`` and the default reaction form URLs
      (``Reactieformulier-URL zienswijze`` and ``Reactieformulier-URL bezwaar``), select
      the Documents API service and save. At this point, an error message that the
      Catalogi API service is not available is expected.

      .. note:: The Open Zaak instance of the stack already has a catalogus for RSIN
         ``100000198``. If you use this RSIN, also fill in the ``Catalogus-URL``
         ``http://openzaak.docker.internal:8001/catalogi/api/v1/catalogussen/770dcb62-2469-4353-a2a7-e619df7e061f``.

   b. Run the setup command, which creates the Catalogi API service from the Documents
      API service of Open Zaak:

      .. code:: bash

         docker compose exec web python src/manage.py setup_catalogi_api

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
