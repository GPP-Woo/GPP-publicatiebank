.. _installation_performance_testing:

Performance testing
===================

The repository contains a load test you can run against your own deployment of
GPP-publicatiebank. Use it to find out how much load an installation handles, and to
tune its deployment: run the same load before and after changing a setting, and compare
the results.

The load test is a `Locust`_ file in the ``performance_test`` directory. It simulates
three kinds of users of the API:

**Readers**
    API clients such as GPP-app, GPP-zoeken or a burgerportaal, browsing the API: they
    list and retrieve publications, documents and reference data, and download
    documents.

**Editors**
    Create a concept publication, edit it, search for it and delete it again.

**Uploaders**
    Upload documents, like during a bulk upload: create a concept publication, add one
    or more documents to it, upload all file parts, wait until the publicatiebank marks
    the upload as complete, download the result and check it. They then delete what
    they created.

You choose how many users of each kind take part, and how big the uploaded documents
are.

.. _Locust: https://locust.io/

What the test does to your data
-------------------------------

The test creates real publications and documents, so make sure that is acceptable in
the environment you test.

* Everything is created as a **concept** publication with a title starting with
  ``Prestatietest``. Concept publications are never published or sent to GPP-zoeken.
* With ``--publish`` the publications and their documents are published instead, so
  GPP-zoeken indexes them and they are publicly findable while the test runs. At the
  end of each iteration they are revoked, which removes them from the search index,
  but they are not deleted: deleting through the API would leave them in the search
  index. Every revoked publication is written to ``--revoked-file``, one JSON object
  per line with the UUIDs of the publication and its documents, for example::

      {"publicatie":"3eaaaab8-...","documenten":["6721c114-..."]}

  Delete them once the celery workers have finished the queued work, or in the admin,
  where deleting also removes them from the search index. Until then, their files stay
  in the Documents API.
* Every uploader and editor deletes what it created, including the files in the
  Documents API, also when the run ends halfway. Only when the load test itself is
  killed (for example by pressing Ctrl+C twice) can some publications remain. You can
  find them in the admin by searching for ``Prestatietest``.
* All requests carry the audit headers with user ``prestatietest``, so they are easy
  to recognise in the audit logs.

Uploads go through the complete processing pipeline: the Documents API stores the file
parts, and a celery worker removes the metadata from PDF and ZIP files. With
``--publish``, a celery worker then also sends each document to GPP-zoeken, which
downloads it from the publicatiebank to index it. The test is therefore as heavy on the
Documents API (for example Open Zaak), GPP-zoeken and the celery workers as it is on the
publicatiebank itself.

Requirements
------------

* A checkout of this repository.
* Python 3.12 or newer, *or* Docker.
* The URL of the publicatiebank you want to test. The load generator must be able to
  reach it, and the publicatiebank must have a working Documents API configured.
* An API key with read and write permissions. Create one in the admin under
  **API-toegang** > **Applicatie-API-keys**.

Installation
------------

Install Locust in a virtual environment of its own. The test does not need any of the
publicatiebank's own dependencies:

.. code-block:: bash

    python3 -m venv .venv-perf
    .venv-perf/bin/pip install -r requirements/perf.txt

Alternatively, run it in a container. The examples below use the virtual environment.
With Docker, replace ``.venv-perf/bin/locust`` with:

.. code-block:: bash

    docker run --rm -it -p 8089:8089 -v "$PWD:/repo:ro" -w /repo python:3.12-slim sh -c \
        "pip install -q -r requirements/perf.txt && locust -f performance_test/locustfile.py ..."

Running a test
--------------

With the web interface
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    .venv-perf/bin/locust -f performance_test/locustfile.py \
        --host https://publicatiebank.example.nl --token <API key>

Open http://localhost:8089, fill in the number of readers, editors and uploaders, and
set **Number of users** to their total. Charts show the response times and failures
while the test runs.

Without the web interface
~~~~~~~~~~~~~~~~~~~~~~~~~

For repeatable runs, use ``--headless`` with a fixed duration, and save the results:

.. code-block:: bash

    export PERF_TOKEN=<API key>
    .venv-perf/bin/locust -f performance_test/locustfile.py --headless \
        --host https://publicatiebank.example.nl \
        --readers 20 --editors 5 --uploaders 3 --doc-size-mb 1-50 \
        --run-time 10m --csv results/baseline --html results/baseline.html

The number of users is the sum of readers, editors and uploaders. They are started at
one per second; use ``--spawn-rate`` to start them faster.

Options
~~~~~~~

All options can also be set as environment variables, which is the safest way to pass
the API key.

.. list-table::
    :header-rows: 1
    :widths: 25 30 45

    * - Option
      - Environment variable
      - Description
    * - ``--host``
      - ``LOCUST_HOST``
      - Base URL of the publicatiebank.
    * - ``--token``
      - ``PERF_TOKEN``
      - API key.
    * - ``--readers``
      - ``PERF_READERS``
      - Number of readers (default 10).
    * - ``--editors``
      - ``PERF_EDITORS``
      - Number of editors (default 2).
    * - ``--uploaders``
      - ``PERF_UPLOADERS``
      - Number of uploaders (default 2).
    * - ``--doc-size-mb``
      - ``PERF_DOC_SIZE_MB``
      - Document size in MiB: a fixed size like ``50``, or a range like ``1-50``
        (default ``1-20``). In a range, there are as many documents between 1-10
        MiB as between 10-100 MiB: mostly small documents, some large ones.
    * - ``--docs-per-publication``
      - ``PERF_DOCS_PER_PUBLICATION``
      - Documents per publication (default 1).
    * - ``--file-type``
      - ``PERF_FILE_TYPE``
      - ``pdf`` (default) or ``zip`` go through metadata stripping in celery,
        ``bin`` skips it.
    * - ``--completion-timeout``
      - ``PERF_COMPLETION_TIMEOUT``
      - Seconds an upload may take to complete before it counts as failed (default 600).
    * - ``--publish``
      - ``PERF_PUBLISH``
      - Publish the publications, so their documents are also indexed by GPP-zoeken.
        Needs an active organisation (**Metadata** > **Organisaties**) to use as
        publisher.
    * - ``--revoked-file``
      - ``PERF_REVOKED_FILE``
      - With ``--publish``: the file the revoked publications are appended to
        (default ``revoked.jsonl``). It must be writable, so in a container, point it
        to a mounted directory.
    * - ``--keep-data``
      - ``PERF_KEEP_DATA``
      - Do not delete the created publications and documents (with ``--publish``: do
        not revoke them either).
    * - ``--run-time``
      - ``LOCUST_RUN_TIME``
      - Duration, e.g. ``10m``.
    * - ``--csv``, ``--html``
      -
      - Save the results.

When the run time is over, users finish what they are doing, including cleaning up,
for at most ``--stop-timeout`` seconds. Unless you set it, that is the
``--completion-timeout``.

Run ``locust -f performance_test/locustfile.py --help`` for all of Locust's own options.

Example scenarios
-----------------

**Normal use.** Mostly reading, with some editing and the occasional upload:

.. code-block:: bash

    --readers 50 --editors 5 --uploaders 1 --doc-size-mb 0.1-10 --run-time 15m

**Bulk upload.** Several people or systems uploading large numbers of documents at the
same time. This is where most problems show up:

.. code-block:: bash

    --readers 5 --editors 0 --uploaders 10 --doc-size-mb 1-100 --run-time 15m

**Large documents.** Find out up to which size uploads remain reliable by repeating
a run with increasing fixed sizes:

.. code-block:: bash

    --readers 0 --editors 0 --uploaders 3 --doc-size-mb 250 --run-time 10m

**Soak test.** A moderate load for a long time, to find memory that keeps growing:

.. code-block:: bash

    --readers 20 --editors 2 --uploaders 3 --doc-size-mb 1-50 --run-time 2h

Reading the results
-------------------

Locust reports every type of request separately, by method and path, for example
``PUT /api/v2/documenten/[uuid]/bestandsdelen/[uuid]`` for the file part uploads. For
each it shows the number of requests, the number of failures, the throughput and the
response time percentiles.

One line is not a single request: **FLOW document ready** is the time from registering
a document until it is completely processed and downloadable. That includes uploading
all file parts and waiting for the celery worker that strips the metadata. A document
counts as failed when any step failed, when it did not complete within
``--completion-timeout``, when the download differs from what the API reports, or when
the stored file is more than 10% larger than the uploaded file. Removing metadata never
makes a file substantially larger.

What to look at:

* **Failures** are the most important signal. The error report at the end (and the
  **Failures** tab in the web interface) shows the status codes and error messages.
  A ``502``/``504`` usually means a proxy in front of the publicatiebank gave up; a
  ``500`` on uploads usually means the Documents API did not respond in time.
* **The 95th percentile** (p95) shows how slow the slowest requests are. An average
  can look fine while one in twenty requests is very slow.
* **Throughput** (requests per second) at the same number of users tells you whether a
  change made the system faster.
* **FLOW document ready** failing with *upload did not complete in time* while the
  part uploads succeed points at the celery workers: they are busy, too few, or crashed
  while processing a document.

Compare a run with an increasing number of users to find where the response times
start to rise or the first failures appear. That is the capacity of the installation.

Tuning a deployment
-------------------

Change one setting at a time and run the same scenario before and after. Save both runs
with ``--csv``, then compare them:

.. code-block:: bash

    python3 performance_test/compare.py results/one-process results/four-processes \
        --labels 1 4

This is part of a real comparison, made on a laptop, of ``UWSGI_PROCESSES=1`` with the
default of 4 (60 readers, 4 editors, 4 uploaders):

.. code-block:: none

    request                                             req/s 1  req/s 4  fail 1  fail 4  p50 ms 1  p50 ms 4      Δ  p95 ms 1  p95 ms 4     Δ
    --------------------------------------------------  -------  -------  ------  ------  --------  --------  -----  --------  --------  ----
    POST /api/v2/documenten                                0.09     0.90  100.0%    3.8%     11000       180   -98%     30000      1000  -97%
    PUT /api/v2/documenten/[uuid]/bestandsdelen/[uuid]        -     1.49       -    1.5%         -       170                -       330
    GET /api/v2/publicaties/[uuid]                         0.90     5.42    0.0%    0.0%       730        21   -97%     11000       450  -96%
    FLOW document ready                                       -     0.84       -    1.3%         -       600                -      1600
    Aggregated                                             5.08    36.58    1.8%    0.4%      8800        35  -100%     30000      6700  -78%

With a single process every request waits for the one before it, and no upload
succeeds at all (see the note on the Documents API below). A dash means the request was
not made in that run.

Results vary between runs, so only trust differences that are large, or that you see
again when repeating both runs. Runs of 10 minutes or more give more stable numbers.

The settings that matter most:

==========================================  ==============================================
Setting                                     Effect
==========================================  ==============================================
``UWSGI_PROCESSES``, ``UWSGI_THREADS``      How many requests a publicatiebank container
                                            handles at the same time (default 4 and 1).
                                            Each process uses its own memory. Raise this
                                            if requests queue up (response times rise
                                            while CPU is still available). Uploads and
                                            downloads occupy a process for their whole
                                            duration. Never use a single process and
                                            thread: while registering a document, Open
                                            Zaak calls back to the publicatiebank, which
                                            then has nobody left to answer.
``UWSGI_HTTP_TIMEOUT``, ``UWSGI_HARAKIRI``  How long a request may take, in seconds
                                            (default 1800). Large uploads on slow storage
                                            need time. Proxies and ingresses in front of
                                            the publicatiebank have their own timeouts
                                            and maximum body size.
``DOCUMENTS_API_SLOW_OPERATIONS_TIMEOUT``   How long the publicatiebank waits for the
                                            Documents API while uploading a file part or
                                            unlocking a document (default 300 s).
Timeout of the Documents API service        All other Documents API calls, including
                                            registering a new document, use the timeout
                                            of the service in the admin (**Configuratie**
                                            > **Services**, default 10 s). Registering
                                            a large document can take longer when the
                                            Documents API is busy, which shows up as
                                            ``500`` errors on ``POST /api/v2/documenten``.
``CELERY_WORKER_CONCURRENCY``               How many documents a celery worker processes
                                            at the same time (default 1). Metadata
                                            stripping holds the document on disk and
                                            partly in memory.
``CELERY_WORKER_MAX_TASKS_PER_CHILD``,      Replace a worker process after this many
``CELERY_WORKER_MAX_MEMORY_PER_CHILD``      tasks (default 50) or this much memory, in
                                            KiB, so that memory does not keep growing.
Number of replicas and memory limits        More publicatiebank or celery containers, and
                                            enough memory for each.
Documents API part size                     The Documents API splits uploads into parts.
                                            For Open Zaak this is
                                            ``DOCUMENTEN_UPLOAD_CHUNK_SIZE``. Small parts
                                            mean many requests per document; large parts
                                            mean more memory per request.
==========================================  ==============================================

Watching memory during a test
-----------------------------

The load test only sees the API from the outside. Memory problems, such as celery
workers that keep growing or containers that get killed for using too much memory, you
have to watch on the servers themselves. Record memory use while the test runs, for
example every 10 seconds.

On Kubernetes:

.. code-block:: bash

    while true; do
        kubectl top pod --namespace <namespace> --no-headers | sed "s/^/$(date +%T) /"
        sleep 10
    done | tee memory.log

Afterwards, check whether containers were restarted, and why:

.. code-block:: bash

    kubectl get pods --namespace <namespace>   # see the RESTARTS column
    kubectl describe pod <pod> --namespace <namespace> | grep -A3 "Last State"  # OOMKilled?

With Docker Compose:

.. code-block:: bash

    while true; do
        docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' | sed "s/^/$(date +%T) /"
        sleep 10
    done | tee memory.log

What to look for:

* Memory that rises during the test and goes back down afterwards is normal.
* Memory of a celery worker that keeps rising during a soak test, without dropping
  back, means that worker processes are not replaced often enough. Lower
  ``CELERY_WORKER_MAX_TASKS_PER_CHILD`` or set ``CELERY_WORKER_MAX_MEMORY_PER_CHILD``.
* A container that is killed (``OOMKilled``) needs a higher memory limit, or less
  concurrency (fewer uwsgi processes or celery workers per container).
* Watch the Documents API as well. Open Zaak, for example, holds file parts in memory
  while it processes them, so its memory use grows with the size of the uploads.

The load generator
------------------

Locust itself needs resources too. Every uploader holds the document it uploads in
memory, so 10 uploaders with 100 MiB documents need about 1 GiB of memory on the
machine that runs the test. One Locust process uses one CPU core; if the machine running
the test shows a CPU usage warning, add ``--processes -1`` to use all cores. Results
are only meaningful when the load generator is not the bottleneck, and when its network
connection to the publicatiebank is not either.

Testing locally with Docker Compose
-----------------------------------

You can try the test against the :ref:`Docker Compose <installation_docker_compose>`
setup on your own computer. A laptop is not representative of a real deployment, but
it is useful to check that the test works, or to see the effect of a code change.

1. Open Zaak splits uploads in parts of 100 bytes in this setup, which is useful when
   developing but unrealistic. Start the stack with a realistic part size instead:

   .. code-block:: bash

       DOCUMENTEN_UPLOAD_CHUNK_SIZE=5242880 docker compose up -d

2. Configure the Documents API in the admin, under **Configuratie** > **Algemene
   instellingen**: select the Open Zaak Documenten API service and fill in an RSIN.

3. Open Zaak looks up the document type at the URL the publicatiebank was called with,
   and only knows the publicatiebank as ``host.docker.internal:8000``. Either add
   ``host.docker.internal`` to your hosts file (see ``INSTALL.rst``) and use
   ``--host http://host.docker.internal:8000``, or run the test in a container:

   .. code-block:: bash

       docker run --rm -it -p 8089:8089 --add-host host.docker.internal:host-gateway \
           -v "$PWD:/repo:ro" -w /repo \
           -e PERF_TOKEN=insecure-ea1a8d297e3b2d3313b8a30b18959c3 \
           python:3.12-slim sh -c "pip install -q -r requirements/perf.txt && \
               locust -f performance_test/locustfile.py --host http://host.docker.internal:8000"
