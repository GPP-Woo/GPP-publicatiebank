from decouple import Csv, Undefined, undefined
from open_api_framework.conf.utils import config as _config
from typing_extensions import deprecated


@deprecated("To be replaced with maykin_common.config")
def config[T](option: str, default: T | Undefined = undefined, *args, **kwargs) -> T:
    """
    Pull a config parameter from the environment.

    Read the config variable ``option``. If it's optional, use the ``default`` value.
    Input is automatically cast to the correct type, where the type is derived from the
    default value if possible.

    Pass ``split=True`` to split the comma-separated input into a list.
    """
    if kwargs.get("split") is True:  # pragma: no cover
        kwargs.pop("split")
        kwargs["cast"] = Csv()
        if default == []:
            default = ""  # pyright: ignore
    kwargs["default"] = default
    return _config(option, *args, **kwargs)  # pyright: ignore


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
