# ruff: noqa: F405
from django.core import validators
from django.utils.translation import gettext_lazy as _

import django_stubs_ext
import structlog
from open_api_framework.conf.base import *  # noqa
from upgrade_check import UpgradeCheck, VersionRange
from vng_api_common.conf.api import BASE_REST_FRAMEWORK

from woo_publications.logging.processors import drop_user_agent_in_dev

from .utils import config

django_stubs_ext.monkeypatch()


TIME_ZONE = "Europe/Amsterdam"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = INSTALLED_APPS + [
    # External applications.
    "capture_tag",
    "hijack",
    "hijack.contrib.admin",
    "maykin_common",
    "timeline_logger",
    "treebeard",
    "drf_polymorphic",
    # Project applications.
    "woo_publications.accounts",
    "woo_publications.api",
    "woo_publications.config",
    "woo_publications.logging",
    "woo_publications.metadata",
    "woo_publications.publications",
    "woo_publications.utils",
]

INSTALLED_APPS.remove("vng_api_common")
INSTALLED_APPS.remove("notifications_api_common")

MIDDLEWARE = MIDDLEWARE + [
    "hijack.middleware.HijackUserMiddleware",
    # NOTE: affects *all* requests, not just API calls. We can't subclass (yet) either
    # to modify the behaviour, since drf-spectacular has a bug in its `issubclass`
    # check, which is unreleased at the time of writing:
    # https://github.com/tfranzel/drf-spectacular/commit/71c7a04ee8921c01babb11fbe2938397a372dac7
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",
]

# Remove unused/irrelevant middleware added by OAF
MIDDLEWARE.remove("corsheaders.middleware.CorsMiddleware")
MIDDLEWARE.remove("csp.contrib.rate_limiting.RateLimitedCSPMiddleware")

#
# LOGGING
#
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
    "django_structlog.middlewares.RequestMiddleware",
)

# Override/fix the default -> TODO: check if there's an open-api-framework update
# available
LOG_LEVEL = config(
    "LOG_LEVEL",
    default="INFO",
    help_text=(
        "Control the verbosity of logging output. "
        "Available values are ``CRITICAL``, ``ERROR``, ``WARNING``, ``INFO`` "
        "and ``DEBUG``."
    ),
)
# TODO - open-api-framework reads the LOG_REQUEST envvar (!)
LOG_OUTGOING_REQUESTS = LOG_REQUESTS

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # structlog - foreign_pre_chain handles logs coming from stdlib logging module,
        # while the `structlog.configure` call handles everything coming from structlog.
        # They are mutually exclusive.
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.ExtraAdder(),
                drop_user_agent_in_dev,
                structlog.stdlib.PositionalArgumentsFormatter(),
            ],
        },
        "plain_console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.ExtraAdder(),
                drop_user_agent_in_dev,
                structlog.stdlib.PositionalArgumentsFormatter(),
            ],
        },
        # legacy
        "outgoing_requests": {"()": HttpFormatter},
    },
    "filters": {},
    "handlers": {
        "null": {  # used by the ``mute_logging`` util
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": config("LOG_FORMAT_CONSOLE", default="json"),
        },
        # replaces the "django" and "project" handlers - in containerized applications
        # the best practices is to log to stdout (use the console handler).
        "json_file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGGING_DIR / "application.jsonl",
            "formatter": "json",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "log_outgoing_requests": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            # TODO: use nicer formatter, OIP has something?
            "formatter": "outgoing_requests",
        },
        "save_outgoing_requests": {
            "level": "DEBUG",
            "class": "log_outgoing_requests.handlers.DatabaseOutgoingRequestsHandler",
        },
    },
    "loggers": {
        "woo_publications": {
            "handlers": ["json_file"] if not LOG_STDOUT else ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.request": {
            "handlers": ["json_file"] if not LOG_STDOUT else ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # suppress django.server request logs because those are already emitted by
        # django-structlog middleware
        "django.server": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "mozilla_django_oidc": {
            "handlers": ["json_file"] if not LOG_STDOUT else ["console"],
            "level": LOG_LEVEL,
        },
        "log_outgoing_requests": {
            "handlers": (
                ["log_outgoing_requests", "save_outgoing_requests"]
                if LOG_OUTGOING_REQUESTS
                else []
            ),
            "level": "DEBUG",
            "propagate": True,
        },
        "django_structlog": {
            "handlers": ["json_file"] if not LOG_STDOUT else ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        drop_user_agent_in_dev,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # structlog.processors.ExceptionPrettyPrinter(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

#
# SECURITY settings
#

CSRF_FAILURE_VIEW = "maykin_common.views.csrf_failure"

#
# Custom settings
#
PROJECT_NAME = _("WOO Publications")
ENABLE_ADMIN_NAV_SIDEBAR = config("ENABLE_ADMIN_NAV_SIDEBAR", default=False)

# Displaying environment information
ENVIRONMENT_LABEL = config("ENVIRONMENT_LABEL", ENVIRONMENT)
ENVIRONMENT_BACKGROUND_COLOR = config("ENVIRONMENT_BACKGROUND_COLOR", "orange")
ENVIRONMENT_FOREGROUND_COLOR = config("ENVIRONMENT_FOREGROUND_COLOR", "black")
SHOW_ENVIRONMENT = config("SHOW_ENVIRONMENT", default=True)

# This setting is used by the csrf_failure view (accounts app).
# You can specify any path that should match the request.path
# Note: the LOGIN_URL Django setting is not used because you could have
# multiple login urls defined.
LOGIN_URLS = [reverse_lazy("admin:login")]

# Default (connection timeout, read timeout) for the requests library (in seconds)
REQUESTS_DEFAULT_TIMEOUT = (10, 30)

# The Identifier of `inspanningsverplichting` from the gov origins list for the
# Information Categories.
INSPANNINGSVERPLICHTING_IDENTIFIER = (
    "https://identifier.overheid.nl/tooi/def/thes/kern/c_816e508d"
)

# Image field validator settings
ALLOWED_IMG_EXTENSIONS = config(
    "ALLOWED_IMG_EXTENSIONS",
    default=[
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
    ],
    help_text="The allowed image extensions that we support.",
    group="Image upload settings",
)
assert set(ALLOWED_IMG_EXTENSIONS) <= set(
    validators.get_available_image_extensions()
), "img file type not supported"

MAX_IMG_SIZE = config(
    "MAX_IMG_SIZE",
    default=1_000_000,
    help_text="The maximum size of images in bytes.",
    group="Image upload settings",
)
MAX_IMG_HEIGHT = config(
    "MAX_IMG_HEIGHT",
    default=600,
    help_text="The maximum image height of images in pixels.",
    group="Image upload settings",
)
MAX_IMG_WIDTH = config(
    "MAX_IMG_WIDTH",
    default=600,
    help_text="The maximum image width of images in pixels.",
    group="Image upload settings",
)

##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

#
# Django-Admin-Index
#
ADMIN_INDEX_SHOW_REMAINING_APPS = False
ADMIN_INDEX_SHOW_REMAINING_APPS_TO_SUPERUSERS = True
ADMIN_INDEX_DISPLAY_DROP_DOWN_MENU_CONDITION_FUNCTION = (
    "maykin_common.django_two_factor_auth.should_display_dropdown_menu"
)

#
# DJANGO-AXES
#
# The number of login attempts allowed before a record is created for the
# failed logins. Default: 3
AXES_FAILURE_LIMIT = 10
# If set, defines a period of inactivity after which old failed login attempts
# will be forgotten. Can be set to a python timedelta object or an integer. If
# an integer, will be interpreted as a number of hours. Default: None
AXES_COOLOFF_TIME = 1

#
# MAYKIN-2FA
#
# It uses django-two-factor-auth under the hood so you can configure
# those settings too.
#
# we run the admin site monkeypatch instead.
# Relying Party name for WebAuthn (hardware tokens)
TWO_FACTOR_WEBAUTHN_RP_NAME = f"WOO Publications ({ENVIRONMENT})"


#
# DJANGO-HIJACK
#
HIJACK_PERMISSION_CHECK = "maykin_2fa.hijack.superusers_only_and_is_verified"
HIJACK_INSERT_BEFORE = (
    '<div class="content">'  # note that this only applies to the admin
)

# Subpath (optional)
# This environment variable can be configured during deployment.
SUBPATH = (
    f"/{_subpath.strip('/')}" if (_subpath := config("SUBPATH", default="")) else ""
)

#
# DJANGO REST FRAMEWORK
#

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["PAGE_SIZE"] = 10
REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"
REST_FRAMEWORK["DEFAULT_FILTER_BACKENDS"] = (
    "django_filters.rest_framework.DjangoFilterBackend",
)
REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"] = (
    "woo_publications.api.pagination.DynamicPageSizePagination"
)
REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = (
    "woo_publications.api.permissions.TokenAuthPermission",
    "woo_publications.api.permissions.AuditHeaderPermission",
)
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = (
    "woo_publications.api.authorization.TokenAuthentication",
)
REST_FRAMEWORK["EXCEPTION_HANDLER"] = "woo_publications.api.views.exception_handler"

API_VERSION = "2.0.0"

EXCLUDED_API_PATH_PREFIXES = ("/api/v1",)
assert isinstance(EXCLUDED_API_PATH_PREFIXES, str | tuple), (
    "`EXCLUDED_API_PATH_PREFIXES` must be a string or a tuple."
)

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": "/api/v2",
    "TITLE": "WOO Publications",
    "DESCRIPTION": _(
        """
## Documentation

The Woo Publications API enables client applications to consult and manage
the publications of documents for transparency of governance. This API
documentation contains three logical 'domains'.

### Domains

**Metadata**

Publications and their related documents must have certain metadata attached
to them. The metadata endpoints allow client applications to retrieve (and
in some resources also create/update) the available metadata.

* [Organisations](#tag/Organisaties): known government organisations, such
  as municipalities, provices...
* [Information categories](#tag/Informatiecategorieen): the prescribed
  categories for the [DiWoo](https://standaarden.overheid.nl/diwoo/metadata)
  standard, optionally extended with organization-specific categories.
* [Themes](#tag/Themas): a tree structure of parent/child themes to further
  describe what publications are about

**Publications**

* [Publications](#tag/Publicaties): a publication is a logical unit of
  information to be made public. It may contain one or more documents.
  Metadata is typically attached to a publication rather than the contained
  documents.
* [Documents](#tag/Documenten): the actual files/documents that are being
  made public and will be indexed in the search engine(s).

**Catalogi API**

The [Catalogi API](#tag/Catalogi-API) endpoint(s) are an implementation
detail of how this API works. Client applications do not have to worry about
them.

They are required to be able to re-use the Documenten API for the actual
document file storage.

### Authentication

**API key**

The API endpoints require authentication, for which you need an API key. API
keys are managed in the admin interface (see the functional documentation).

Once you have an API key, ensure every request has the necessary header:

    Authorization: Token my-example-api-key

Replace `my-example-api-key` with your actual API key.

**Audit headers**

Additionally, most endpoints require request headers to be set for audit
purposes:

    Audit-User-ID: unique-identifier@example.com
    Audit-User-Representation: Alice B. Tables
    Audit-Remarks: Retrieving own publications

"""
    ),
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "maykin_common.drf_spectacular.hooks.remove_invalid_url_defaults",
    ],
    "PREPROCESSING_HOOKS": [
        "woo_publications.api.drf_spectacular.hooks.remove_excluded_api_paths",
    ],
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": True,
    "TOS": None,
    "CONTACT": {
        "url": "https://github.com/GPP-Woo/GPP-publicatiebank",
        "email": "support@maykinmedia.nl",
    },
    "LICENSE": {
        "name": "EUPL",
        "url": "https://github.com/GPP-Woo/GPP-publicatiebank/blob/main/LICENSE.md",
    },
    "VERSION": API_VERSION,
    "TAGS": [],
    "EXTERNAL_DOCS": {
        "description": "Functional and technical documentation",
        "url": "https://gpp-publicatiebank.readthedocs.io/",
    },
}

#
# ZGW-CONSUMERS
#
ZGW_CONSUMERS_IGNORE_OAS_FIELDS = True

#
# DJANGO-SENDFILE2
#
SENDFILE_BACKEND = config("SENDFILE_BACKEND", default="django_sendfile.backends.nginx")
SENDFILE_ROOT = PRIVATE_MEDIA_ROOT
SENDFILE_URL = PRIVATE_MEDIA_URL

#
# CELERY - async task queue
#
# CELERY_BROKER_URL  defined in open-api-framework
# CELERY_RESULT_BACKEND  defined in open-api-framework

# Add (by default) 1 (soft), 5 (hard) minute timeouts to all Celery tasks.
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_HARD_TIME_LIMIT", default=5 * 60)  # hard
CELERY_TASK_SOFT_TIME_LIMIT = config(
    "CELERY_TASK_SOFT_TIME_LIMIT", default=1 * 60
)  # soft

CELERY_BEAT_SCHEDULE = {}

# Only ACK when the task has been executed. This prevents tasks from getting lost, with
# the drawback that tasks should be idempotent (if they execute partially, the mutations
# executed will be executed again!)
CELERY_TASK_ACKS_LATE = True

# ensure that no tasks are scheduled to a worker that may be running a very long-running
# operation, leading to idle workers and backed-up workers. The `-O fair` option
# *should* have the same effect...
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

#
# DJANGO-UPGRADE-CHECK
#
UPGRADE_CHECK_PATHS = {
    "1.2.0": UpgradeCheck(VersionRange(minimum="1.0.0")),
}

#
# DJANGO-STRUCTLOG
#
DJANGO_STRUCTLOG_IP_LOGGING_ENABLED = False
DJANGO_STRUCTLOG_CELERY_ENABLED = True
