"""
Bootstrap the environment.

Load the secrets from the .env file and store them in the environment, so
they are available for Django settings initialization.

.. warning::

    do NOT import anything Django related here, as this file needs to be loaded
    before Django is initialized.
"""

import os
from pathlib import Path

from django.conf import settings

import structlog
from dotenv import load_dotenv
from requests import Session

logger = structlog.stdlib.get_logger(__name__)


def setup_env():
    # load the environment variables containing the secrets/config
    dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "woo_publications.conf.dev")

    structlog.contextvars.bind_contextvars(source="app")
    monkeypatch_requests()


def monkeypatch_requests():
    """
    Add a default timeout for any requests calls.

    Clean up the code by removing the try/except if requests is installed, or removing
    the call to this function in setup_env if it isn't
    """
    if hasattr(Session, "_original_request"):  # pragma: no cover
        logger.debug("session_already_patched", has_attribute="_original_request")
        return

    Session._original_request = Session.request  # pyright: ignore

    def new_request(self, *args, **kwargs):
        kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
        return self._original_request(*args, **kwargs)

    Session.request = new_request
