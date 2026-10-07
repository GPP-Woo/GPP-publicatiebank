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

The Woo Publications component uses the
:ref:`information categories <admin_metadata_index_information_categories>` to describe
the document type ("informatieobjecttype") for the Documents API. The permissions to the
Documents API are based on these document types.

**Permission scopes**

* ``documenten.aanmaken``
* ``documenten.bijwerken``

Woo Publications requires the scopes listed above, for all information categories.

The API resource URLs for all information categories are available on a page in the
admin. Navigate to **Admin** > **Metadata** > **Information categories**. In the top
right, click the **View API resource URLs** button.

The list page displays all information categories, grouped by their origin with the
fully qualified resource URLs required by the Authorisations API.

Known applications/products providing a Documents API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* `Open Zaak <https://open-zaak.readthedocs.io/>`_

.. tip:: If you're a vendor, please create a PR to add your product to this list.

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

.. warning:: Run **exactly one** Celery beat process. Without it, periodic tasks are
   never scheduled and silently don't run. With more than one, every periodic task
   is scheduled multiple times.

Celery beat keeps its schedule state in ``/app/celerybeat``. This location does not
require persistent storage, but if beat is restarted around the time a task is due,
that run may be skipped until the next scheduled moment.

Reverse proxy
-------------

It's recommended to set up a reverse proxy (like nginx or a Kubernetes ingress/gateway)
before the application container, as these pieces of software are designed to scale
well. They can prevent the application containers from becoming overloaded.

Configuring a reverse proxy or Kubernetes cluster is out of scope for this project, but
some implementation details are relevant and they are listed below.

Allow streaming of document downloads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Uploaded documents in the API are also downloaded again - especially by the National
Search Index (DiWoo) which indexes the documents, but ultimately also by interested
parties like citizens, journalists...

Our download API endpoint (``/api/v1/documenten/:uuid/download``) sends a response
header ``X-Accel-Buffering: off`` to the reverse proxy to promote synchronous streaming
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
