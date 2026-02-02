from collections.abc import Callable

from maykin_common.config import config as _config
from open_api_framework.conf.utils import config as _legacy_config


def wrap_config[T, **P](wrapped: Callable[P, T]):
    def inner(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        help_text = kwargs.pop("help_text", "")
        group = kwargs.pop("group", "")

        # ensure the docs registration stuff is still happening
        option = args[0]
        assert isinstance(option, str)
        _legacy_kwargs = {**kwargs, "help_text": help_text, "group": group}
        _legacy_config(option, **_legacy_kwargs)  # type: ignore

        # can't handle the typing overlaods in a decorator...
        return wrapped(*args, **kwargs)

    return inner


config = wrap_config(_config)


def mute_logging(config: dict) -> None:  # pragma: no cover
    """
    Disable (console) output from logging.

    :arg config: The logging config, typically the django LOGGING setting.
    """

    # set up the null handler for all loggers so that nothing gets emitted
    for name, logger in config["loggers"].items():
        if name == "flaky_tests":
            continue
        logger["handlers"] = ["null"]

    # some tooling logs to a logger which isn't defined, and that ends up in the root
    # logger -> add one so that we can mute that output too.
    config["loggers"].update(
        {
            "": {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
        }
    )
