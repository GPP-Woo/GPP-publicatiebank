.. _installation_requirements:

Requirements
============

Documents API
-------------

The Woo Publications component uses the VNG
`Documents API <https://vng-realisatie.github.io/gemma-zaken/standaard/documenten/>`_
standard for the actual persisting of (published) documents. This means that you must
provide or provision an API provider that implements this standard. You must also
configure some authorization aspects in the
`Authorisations API <https://vng-realisatie.github.io/gemma-zaken/standaard/autorisaties/>`_
used by the chosen Documents API.

What you'll need
~~~~~~~~~~~~~~~~

* Access to the admin environment of the Woo Publications component, e.g.
  ``https://woo-publications.example.com/admin/``.
* Configure the :ref:`Documents API service <configuration_services_documents_api>`.

Configuration for the Authorisations API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every document in the Documents API has a document type ("informatieobjecttype").
The Woo Publications component gives every
:ref:`information category <admin_metadata_index_information_categories>` its own
informatieobjecttype in the :ref:`Catalogi API <installation_requirements_catalogi_api>`,
and documents get the informatieobjecttype of the information category of their
publication. The permissions to the Documents API are based on these document types.

**Permission scopes**

* ``documenten.lezen``
* ``documenten.aanmaken``
* ``documenten.bijwerken``
* ``documenten.verwijderen``
* ``documenten.lock``

Woo Publications requires the scopes listed above, for all informatieobjecttypen of the
information categories and for the default informatieobjecttype (see below). It reads
documents to serve downloads, creates and updates documents, locks and unlocks documents
for (large file) uploads, and deletes documents when they are deleted in Woo
Publications.

.. tip:: In Open Zaak, an application with "heeft alle autorisaties" (all permissions)
   doesn't need permissions per informatieobjecttype.

The API resource URLs of the informatieobjecttypen are available on a page in the
admin, once the Catalogi API is configured. Navigate to **Admin** > **Metadata** >
**Information categories**. In the top right, click the **View API resource URLs**
button.

The list page displays all information categories, grouped by their origin, with the
URLs of their informatieobjecttypen in the Catalogi API. Use these URLs to configure
the permissions in the Authorisations API.

.. note:: Before version 3.0.0, the informatieobjecttypen were served by Woo
   Publications itself (``.../catalogi/api/v1/informatieobjecttypen/...``). Permissions
   that refer to those URLs no longer apply - after upgrading, grant the permissions for
   the new informatieobjecttypen in the Catalogi API.

Known applications/products providing a Documents API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* `Open Zaak <https://open-zaak.readthedocs.io/>`_

.. tip:: If you're a vendor, please create a PR to add your product to this list.

.. _installation_requirements_catalogi_api:

Catalogi API
------------

The Woo Publications component manages the document types ("informatieobjecttypen") of
the :ref:`information categories <admin_metadata_index_information_categories>` in a
`Catalogi API <https://vng-realisatie.github.io/gemma-zaken/standaard/catalogi/>`_. It
must be the Catalogi API that the Documents API uses to validate document types; with
Open Zaak, that is the Catalogi API of the same Open Zaak instance.

What you'll need
~~~~~~~~~~~~~~~~

* Configure the :ref:`Catalogi API service <configuration_services_catalogi_api>`.
* The organisation RSIN must be set in the global configuration - the catalogus is
  created for this RSIN.
* With Open Zaak, the Catalogi API (ZTC) component must be enabled.

.. warning:: Since version 3.0.0, the Catalogi API is required. Until it is configured,
   document uploads fail.

Configuration for the Authorisations API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Permission scopes**

* ``catalogi.lezen``
* ``catalogi.schrijven``

Woo Publications creates a catalogus, a default informatieobjecttype for documents of
publications without an information category, and an informatieobjecttype for every
information category.

When you grant the Documents API permissions per document type, include the default
informatieobjecttype. Its URL is shown in the global configuration
(``Default informatieobjecttype url``) and it has the confidentiality level
``vertrouwelijk``, so the maximum confidentiality level must be at least
``vertrouwelijk``.

.. note:: Before version 3.0.0, Open Zaak needed a ZTC service that pointed to Woo
   Publications. This service is no longer used and can be removed.

Processes
---------

The container image provides scripts to start each process that makes up a complete
GPP-publicatiebank deployment. All of them use the same image and environment
variables.

* ``/start.sh`` - the web application (admin and API).
* ``/celery_worker.sh`` - the background task workers, e.g. for synchronising with
  GPP-zoeken and stripping document metadata. You can run as many replicas as needed.
* ``/celery_beat.sh`` - the scheduler for periodic tasks, such as automatically
  revoking publications when their inspection period ("inzagetermijn") has ended.
* ``/celery_flower.sh`` - optional, a web interface to monitor the background tasks.

.. warning:: Run **exactly one** Celery beat process. Without it, periodic tasks are
   never scheduled and silently don't run. With more than one, every periodic task
   is scheduled multiple times.

Celery beat keeps its schedule state in ``/app/celerybeat``. This location does not
require persistent storage, but if beat is restarted around the time a task is due,
that run may be skipped until the next scheduled moment.

Tuning the processes
~~~~~~~~~~~~~~~~~~~~

The start scripts read the following environment variables, in addition to the
:ref:`environment configuration <installation_env_config>`.

**Web application** (``/start.sh``, uWSGI)

* ``UWSGI_PORT``: the port to listen on. Defaults to ``8000``.
* ``UWSGI_PROCESSES``: the number of worker processes. Defaults to ``4``.
* ``UWSGI_THREADS``: the number of threads per process. Defaults to ``1``.
* ``UWSGI_HTTP_TIMEOUT``: the HTTP timeout, in seconds. Defaults to ``1800``.
* ``UWSGI_HARAKIRI``: the maximum time in seconds a request may take before the worker
  is recycled. Defaults to ``1800``.
* ``UWSGI_POST_BUFFERING``: the size (in bytes) above which request bodies are buffered
  to disk. Defaults to ``8192``.
* ``UWSGI_BUFFER_SIZE``: the internal buffer size (in bytes) for request headers.
  Defaults to ``65535``.

Other ``UWSGI_*`` variables are also picked up by uWSGI.

**Background task workers** (``/celery_worker.sh``)

* ``CELERY_WORKER_CONCURRENCY``: the number of concurrent worker processes. Defaults to
  ``1``.
* ``CELERY_WORKER_MAX_TASKS_PER_CHILD``: the number of tasks after which a worker
  process is replaced, which releases its memory. Defaults to ``50``.
* ``CELERY_WORKER_MAX_MEMORY_PER_CHILD``: optional, the maximum memory (in KiB) a worker
  process may use before it is replaced after its current task.
* ``CELERY_WORKER_QUEUE`` and ``CELERY_WORKER_NAME``: the queue to consume and the name
  of the worker. Default to ``celery`` and ``celery@<hostname>``.
* ``CELERY_LOGLEVEL``: the log level of the workers and of Celery beat. Defaults to
  ``INFO``.

Reverse proxy
-------------

It's recommended to set up a reverse proxy (like nginx or a Kubernetes ingress/gateway)
before the application container, as these pieces of software are designed to scale
well. They can prevent the application containers from becoming overloaded.

Configuring a reverse proxy or Kubernetes cluster is out of scope for this project, but
some implementation details are relevant and they are listed below.

Allow streaming of document downloads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Uploaded documents in the API are also downloaded again - especially by the national
`Generieke Woo-Voorziening (GWV) <https://open.overheid.nl/>`_ which indexes the
documents, but ultimately also by interested parties like citizens, journalists...

Our download API endpoint (``/api/v2/documenten/:uuid/download``) sends a response
header ``X-Accel-Buffering: no`` to the reverse proxy to promote synchronous streaming
to the client. Certain nginx (or possibly other reverse proxy implementations)
configuration can lead to this header being ignored.

Most of the time (small files, fast networks...) this shouldn't be a problem, but
especially with larger files (1GB+) being downloaded over slow connections it's possible
the internal nginx buffers fill up and the application container times out when trying
to write the response back to nginx. This results in downloads getting aborted after
about 1GB. Disabling buffering prevents this problem by writing/streaming directly to
the client.

Alternative configurations could be to disable buffering for these endpoints in
particular, in which case the response header can be safely ignored too.

.. seealso:: For all the gritty details, you can read more in
   `github issue 164 <https://github.com/GPP-Woo/GPP-publicatiebank/issues/164>`_.
