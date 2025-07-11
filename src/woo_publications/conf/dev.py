# ruff: noqa: F405
import os
import sys
import warnings

from django.core.paginator import UnorderedObjectListWarning

os.environ.setdefault("DEBUG", "yes")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault(
    "SECRET_KEY",
    "django-insecure-fgggi4*bl2wdg$&@0&)t7ewy5-2!b3l4lhx4_+^zpw%x2i28v8",
)
os.environ.setdefault("IS_HTTPS", "no")
os.environ.setdefault("VERSION_TAG", "dev")

os.environ.setdefault("DB_NAME", "woo_publications")
os.environ.setdefault("DB_USER", "woo_publications")
os.environ.setdefault("DB_PASSWORD", "woo_publications")

os.environ.setdefault("DISABLE_2FA", "yes")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_REQUESTS", "no")
os.environ.setdefault("LOG_STDOUT", "1")
os.environ.setdefault("LOG_FORMAT_CONSOLE", "plain_console")
os.environ.setdefault("VCR_RECORD_MODE", "once")

from .base import *  # noqa isort:skip
from .utils import mute_logging  # noqa isort:skip

# Feel free to switch dev to sqlite3 for simple projects,
# os.environ.setdefault("DB_ENGINE", "django.db.backends.sqlite3")

#
# Standard Django settings.
#
SESSION_ENGINE = "django.contrib.sessions.backends.db"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING["loggers"].update(
    {
        "django": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["json_file"],
            "level": "INFO",
            "propagate": False,
        },
        #
        # See: https://code.djangoproject.com/ticket/30554
        # Autoreload logs excessively, turn it down a bit.
        #
        "django.utils.autoreload": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    }
)

# in memory cache and django-axes don't get along.
# https://django-axes.readthedocs.io/en/latest/configuration.html#known-configuration-problems
CACHES.update(
    {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    }
)

if "test" in sys.argv:
    if "VERBOSE" not in os.environ:
        # shut up logging
        mute_logging(LOGGING)

#
# Library settings
#

ELASTIC_APM["DEBUG"] = config("DISABLE_APM_IN_DEV", default=True)

# Django debug toolbar
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
INTERNAL_IPS = ("127.0.0.1",)

# Django extensions
INSTALLED_APPS += ["django_extensions"]

# DRF - browsable API
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
    "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
)

# Django rosetta
ROSETTA_SHOW_AT_ADMIN_PANEL = True
INSTALLED_APPS += ["rosetta"]

# THOU SHALT NOT USE NAIVE DATETIMES
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

# querysets in api viewsets *must* be ordered
warnings.filterwarnings(
    "error",
    r"Pagination may yield inconsistent results with an unordered object_list: .*",
    UnorderedObjectListWarning,
    r"rest_framework\.pagination",
)

# Override settings with local settings.
try:
    from .local import *  # pyright: ignore # noqa
except ImportError:
    pass
