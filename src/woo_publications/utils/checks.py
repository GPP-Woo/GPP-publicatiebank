import socket

from django.contrib.admin import ModelAdmin
from django.core.checks import Error, Warning, register

from woo_publications.config.admin import GlobalConfigurationAdmin
from woo_publications.logging.admin import TimelineLogProxyAdmin
from woo_publications.logging.service import AdminAuditLogMixin


def get_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from get_subclasses(subclass)
        yield subclass


@register
def check_docker_hostname_dns(app_configs, **kwargs):
    """
    Check that the host.internal.docker hostname resolves to an IP address.

    For simplicity sake we will program interaction tests on this hostname - this
    requires developers (and CI environments) to have their /etc/hosts configured
    properly though, otherwise they'll get weird and hard-to-understand test failures.
    """
    warnings = []
    required_hosts = [
        "host.docker.internal",
        "openzaak.docker.internal",
    ]

    for hostname in required_hosts:
        try:
            socket.gethostbyname(hostname)
        except socket.gaierror:  # pragma: no cover
            warnings.append(
                Warning(
                    f"Could not resolve {hostname} to an IP address (expecting "
                    "127.0.0.1). This will result in test failures.",
                    hint=(
                        f"Add the line '127.0.0.1 {hostname}' to your /etc/hosts file."
                    ),
                    id="utils.W002",
                )
            )

    return warnings


@register
def check_model_admin_includes_logging_mixin(app_configs, **kwargs):  # pragma: no cover
    errors: list[Error] = []

    for admin_cls in get_subclasses(ModelAdmin):
        # ignores outside libraries
        if not admin_cls.__module__.startswith("woo_publications"):
            continue
        if issubclass(admin_cls, AdminAuditLogMixin):
            continue

        # 1. ignore the timeline logger admin, no mutations are possible
        # 2. ignore the config admin, as the mixin is not compatible with how
        #    django-solo works
        if admin_cls in (
            TimelineLogProxyAdmin,
            GlobalConfigurationAdmin,
        ):
            continue

        errors.append(
            Error(
                "AdminAuditLogMixin is missing on the admin class. This mixin is "
                "required to enable audit logging.",
                hint=(
                    "Add AdminAuditLogMixin to the '{admin_cls.__qualname__}' class "
                    "in '{admin_cls.__module__}'."
                ),
                obj=admin_cls,
            )
        )

    return errors
