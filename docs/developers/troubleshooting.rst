.. _developers_troubleshooting:

Troubleshooting
===============

Some common problems can occur during (local) development. We've summarized those here
with a description of the problem and solution.

Can't bind to port 8000 (``docker compose`` or ``runserver``)
-------------------------------------------------------------

**Likely solution**

Ensure you only bring up the Open Zaak service:

.. code-block:: bash

    docker compose up openzaak-web

**Cause**

The ``docker-compose.yml`` also includes the Woo-Publications service itself, which is
mutually exclusive with running it via ``runserver`` on the default port (8000).

You can also run ``runserver`` on a different port instead of the default.


Creating documents fails with an HTTP 500 error
-----------------------------------------------

**Likely solution**

Configure the Catalogi API. With the Open Zaak instance from ``docker compose``, set the
organisation RSIN in the global configuration and run:

.. code-block:: bash

    src/manage.py setup_catalogi_api

See :ref:`configuration_services_catalogi_api` for the details.

**Cause**

Since version 3.0.0, the informatieobjecttypen of the documents are managed in the
Catalogi API of Open Zaak. Until a Catalogi API is configured, there is no
informatieobjecttype to register a document with, so direct uploads fail with an HTTP
500 error and uploads from a URL fail in the background task.


Creating documents fails because Open Zaak can't be reached
-----------------------------------------------------------

**Likely solution**

Ensure that the ``openzaak.docker.internal`` hostname resolves on your host system. You
need to have this entry in your ``/etc/hosts`` file - see :ref:`install_etc_hosts`.

**Cause**

The Documents API and Catalogi API services in the development fixtures point to
``http://openzaak.docker.internal:8001/``. When GPP-publicatiebank runs with
``runserver`` on the host system, this hostname must resolve to ``127.0.0.1``.
