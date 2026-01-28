.. _installation_env_config:

===================================
Environment configuration reference
===================================



Available environment variables
===============================


Required
--------

* ``SECRET_KEY``: Secret key that's used for certain cryptographic utilities. .
* ``ALLOWED_HOSTS``: a comma separated (without spaces!) list of domains that serve the installation. Used to protect against Host header attacks. Defaults to: ``(empty string)``.
* ``CACHE_DEFAULT``: redis cache address for the default cache (this **MUST** be set when using Docker). Defaults to: ``localhost:6379/0``.
* ``CACHE_AXES``: redis cache address for the brute force login protection cache (this **MUST** be set when using Docker). Defaults to: ``localhost:6379/0``.
* ``EMAIL_HOST``: hostname for the outgoing e-mail server (this **MUST** be set when using Docker). Defaults to: ``localhost``.


Database
--------

* ``DB_NAME``: name of the PostgreSQL database. Defaults to: ``woo_publications``.
* ``DB_USER``: username of the database user. Defaults to: ``woo_publications``.
* ``DB_PASSWORD``: password of the database user. Defaults to: ``woo_publications``.
* ``DB_HOST``: hostname of the PostgreSQL database. Defaults to ``db`` for the docker environment, otherwise defaults to ``localhost``.
* ``DB_PORT``: port number of the database. Defaults to: ``5432``.
* ``DB_CONN_MAX_AGE``: The lifetime of a database connection, as an integer of seconds. Use 0 to close database connections at the end of each request — Django’s historical behavior. This setting is ignored if connection pooling is used. Defaults to: ``60``.
* ``DB_POOL_ENABLED``: **Experimental:** Whether to use connection pooling. This feature is not yet recommended for production use. See the documentation for details: https://open-api-framework.readthedocs.io/en/latest/connection_pooling.html. Defaults to: ``False``.
* ``DB_POOL_MIN_SIZE``: The minimum number of connection the pool will hold. The pool will actively try to create new connections if some are lost (closed, broken) and will try to never go below min_size. Defaults to: ``4``.
* ``DB_POOL_MAX_SIZE``: The maximum number of connections the pool will hold. If None, or equal to min_size, the pool will not grow or shrink. If larger than min_size, the pool can grow if more than min_size connections are requested at the same time and will shrink back after the extra connections have been unused for more than max_idle seconds. Defaults to: ``None``.
* ``DB_POOL_TIMEOUT``: The default maximum time in seconds that a client can wait to receive a connection from the pool (using connection() or getconn()). Note that these methods allow to override the timeout default. Defaults to: ``30``.
* ``DB_POOL_MAX_WAITING``: Maximum number of requests that can be queued to the pool, after which new requests will fail, raising TooManyRequests. 0 means no queue limit. Defaults to: ``0``.
* ``DB_POOL_MAX_LIFETIME``: The maximum lifetime of a connection in the pool, in seconds. Connections used for longer get closed and replaced by a new one. The amount is reduced by a random 10% to avoid mass eviction. Defaults to: ``3600``.
* ``DB_POOL_MAX_IDLE``: Maximum time, in seconds, that a connection can stay unused in the pool before being closed, and the pool shrunk. This only happens to connections more than min_size, if max_size allowed the pool to grow. Defaults to: ``600``.
* ``DB_POOL_RECONNECT_TIMEOUT``: Maximum time, in seconds, the pool will try to create a connection. If a connection attempt fails, the pool will try to reconnect a few times, using an exponential backoff and some random factor to avoid mass attempts. If repeated attempts fail, after reconnect_timeout second the connection attempt is aborted and the reconnect_failed() callback invoked. Defaults to: ``300``.
* ``DB_POOL_NUM_WORKERS``: Number of background worker threads used to maintain the pool state. Background workers are used for example to create new connections and to clean up connections when they are returned to the pool. Defaults to: ``3``.


Elastic APM
-----------

* ``ELASTIC_APM_SERVER_URL``: URL where Elastic APM is hosted. Defaults to: ``None``.
* ``ELASTIC_APM_SERVICE_NAME``: Name of the service for this application in Elastic APM. Defaults to ``woo_publications - <environment>``.
* ``ELASTIC_APM_SECRET_TOKEN``: Token used to communicate with Elastic APM. Defaults to: ``default``.
* ``ELASTIC_APM_TRANSACTION_SAMPLE_RATE``: By default, the agent will sample every transaction (e.g. request to your service). To reduce overhead and storage requirements, set the sample rate to a value between 0.0 and 1.0. Defaults to: ``0.1``.


Image upload settings
---------------------

* ``ALLOWED_IMG_EXTENSIONS``: The allowed image extensions that we support. Defaults to: ``['jpg', 'jpeg', 'png', 'gif', 'webp']``.
* ``MAX_IMG_SIZE``: The maximum size of images in bytes. Defaults to: ``1000000``.
* ``MAX_IMG_HEIGHT``: The maximum image height of images in pixels. Defaults to: ``600``.
* ``MAX_IMG_WIDTH``: The maximum image width of images in pixels. Defaults to: ``600``.


Optional
--------

* ``SITE_ID``: The database ID of the site object. You usually won't have to touch this. Defaults to: ``1``.
* ``DEBUG``: Only set this to ``True`` on a local development environment. Various other security settings are derived from this setting!. Defaults to: ``False``.
* ``USE_X_FORWARDED_HOST``: whether to grab the domain/host from the X-Forwarded-Host header or not. This header is typically set by reverse proxies (such as nginx, traefik, Apache...). Note: this is a header that can be spoofed and you need to ensure you control it before enabling this. Defaults to: ``False``.
* ``IS_HTTPS``: Used to construct absolute URLs and controls a variety of security settings. Defaults to the inverse of ``DEBUG``.
* ``EMAIL_PORT``: port number of the outgoing e-mail server. Note that if you're on Google Cloud, sending e-mail via port 25 is completely blocked and you should use 487 for TLS. Defaults to: ``25``.
* ``EMAIL_HOST_USER``: username to connect to the mail server. Defaults to: ``(empty string)``.
* ``EMAIL_HOST_PASSWORD``: password to connect to the mail server. Defaults to: ``(empty string)``.
* ``EMAIL_USE_TLS``: whether to use TLS or not to connect to the mail server. Should be True if you're changing the ``EMAIL_PORT`` to 487. Defaults to: ``False``.
* ``DEFAULT_FROM_EMAIL``: The default email address from which emails are sent. Defaults to: ``woo_publications@example.com``.
* ``LOG_LEVEL``: Control the verbosity of logging output. Available values are ``CRITICAL``, ``ERROR``, ``WARNING``, ``INFO`` and ``DEBUG``. Defaults to: ``INFO``.
* ``LOG_FORMAT_CONSOLE``:  Defaults to: ``json``.
* ``SESSION_COOKIE_AGE``: For how long, in seconds, the session cookie will be valid. Defaults to: ``1209600``.
* ``SESSION_COOKIE_SAMESITE``: The value of the SameSite flag on the session cookie. This flag prevents the cookie from being sent in cross-site requests thus preventing CSRF attacks and making some methods of stealing session cookie impossible.Currently interferes with OIDC. Keep the value set at Lax if used. Defaults to: ``Lax``.
* ``CSRF_COOKIE_SAMESITE``: The value of the SameSite flag on the CSRF cookie. This flag prevents the cookie from being sent in cross-site requests. Defaults to: ``Strict``.
* ``ENVIRONMENT``: An identifier for the environment, displayed in the admin depending on the settings module used and included in the error monitoring (see ``SENTRY_DSN``). The default is set according to ``DJANGO_SETTINGS_MODULE``.
* ``SUBPATH``:  Defaults to: ``(empty string)``.
* ``RELEASE``: The version number or commit hash of the application (this is also sent to Sentry).
* ``NUM_PROXIES``: the number of reverse proxies in front of the application, as an integer. This is used to determine the actual client IP adres. On Kubernetes with an ingress you typically want to set this to 2. Defaults to: ``1``.
* ``CSRF_TRUSTED_ORIGINS``: A list of trusted origins for unsafe requests (e.g. POST). Defaults to: ``[]``.
* ``NOTIFICATIONS_DISABLED``: indicates whether or not notifications should be sent to the Notificaties API for operations on the API endpoints. Defaults to ``True`` for the ``dev`` environment, otherwise defaults to ``False``.
* ``SITE_DOMAIN``: Defines the primary domain where the application is hosted. Defaults to: ``(empty string)``.
* ``SENTRY_DSN``: URL of the sentry project to send error reports to. Default empty, i.e. -> no monitoring set up. Highly recommended to configure this.
* ``DISABLE_2FA``: Whether or not two factor authentication should be disabled. Defaults to: ``False``.
* ``ENABLE_ADMIN_NAV_SIDEBAR``:  Defaults to: ``False``.
* ``ENVIRONMENT_LABEL``:  Defaults to: ``development``.
* ``ENVIRONMENT_BACKGROUND_COLOR``:  Defaults to: ``orange``.
* ``ENVIRONMENT_FOREGROUND_COLOR``:  Defaults to: ``black``.
* ``SHOW_ENVIRONMENT``:  Defaults to: ``True``.
* ``SENDFILE_BACKEND``:  Defaults to: ``django_sendfile.backends.nginx``.
* ``CELERY_TASK_HARD_TIME_LIMIT``:  Defaults to: ``300``.
* ``CELERY_TASK_SOFT_TIME_LIMIT``:  Defaults to: ``60``.
* ``DISABLE_APM_IN_DEV``:  Defaults to: ``True``.
* ``PROFILE``:  Defaults to: ``False``.





Specifying the environment variables
=====================================

There are two strategies to specify the environment variables:

* provide them in a ``.env`` file
* start the component processes (with uwsgi/gunicorn/celery) in a process
  manager that defines the environment variables

Providing a .env file
---------------------

This is the most simple setup and easiest to debug. The ``.env`` file must be
at the root of the project - i.e. on the same level as the ``src`` directory (
NOT *in* the ``src`` directory).

The syntax is key-value:

.. code::

   SOME_VAR=some_value
   OTHER_VAR="quoted_value"


Provide the envvars via the process manager
-------------------------------------------

If you use a process manager (such as supervisor/systemd), use their techniques
to define the envvars. The component will pick them up out of the box.
