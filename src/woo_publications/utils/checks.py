import os
import socket

from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.core.checks import Error, Warning, register
from django.forms import ModelForm

from treebeard.forms import MoveNodeForm

from woo_publications.logging.service import AdminAuditLogMixin


def get_subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from get_subclasses(subclass)
        yield subclass


@register()
def check_modelform_exclude(app_configs, **kwargs):
    """
    Check that ModelForms use Meta.fields instead of Meta.exclude.

    ModelForm.Meta.exclude is dangerous because it doesn't protect against
    fields that are added later. Explicit white-listing is safer and prevents
    bugs such as IMA #645.

    This check piggy-backs on all form modules to be imported during Django
    startup. It won't cover forms that are defined on the fly such as in
    formset factories.
    """
    errors = []

    for form in get_subclasses(ModelForm):
        # MoveNodeForm is generated by treebeard and doesn't pass checks
        if issubclass(form, MoveNodeForm):
            continue
        # ok, fields is defined
        if form._meta.fields or getattr(form.Meta, "fields", None):
            continue

        # no `.fields` defined, so scream loud enough to prevent this
        errors.append(
            Error(
                "ModelForm %s.%s with Meta.exclude detected, this is a bad practice"
                % (form.__module__, form.__name__),
                hint="Use ModelForm.Meta.fields instead",
                obj=form,
                id="utils.E001",
            )
        )

    return errors


@register
def check_missing_init_files(app_configs, **kwargs):
    """
    Check that all packages have __init__.py files.

    If they don't, the code will still run, but tests aren't picked up by the
    test runner, for example.
    """
    errors = []

    for dirpath, dirnames, filenames in os.walk(settings.DJANGO_PROJECT_DIR):
        dirname = os.path.split(dirpath)[1]
        if dirname == "__pycache__":
            continue

        if "__init__.py" in filenames:
            continue

        extensions = [os.path.splitext(fn)[1] for fn in filenames]
        if ".py" not in extensions:
            continue

        errors.append(
            Warning(
                "Directory %s does not contain an `__init__.py` file" % dirpath
                + dirname,
                hint="Consider adding this module to make sure tests are picked up",
                id="utils.W001",
            )
        )

    return errors


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
def check_model_admin_includes_logging_mixin(app_configs, **kwargs):
    errors = []

    for admin in get_subclasses(ModelAdmin):
        # ignores outside libraries
        if not admin.__module__.startswith("woo_publications"):
            continue

        # ignores user model
        if admin.__module__ == "woo_publications.accounts.admin":
            continue

        # ignores the timeline logger admin
        if admin.__name__ == "TimelineLogProxyAdmin":
            continue

        if issubclass(admin, AdminAuditLogMixin):
            continue

        errors.append(
            Error(
                "AdminAuditLogMixin needs to be used for the logging.",
                hint="Add AdminAuditLogMixin to the %s class in %s."
                % (admin.__name__, admin.__module__),
                obj=admin,
            )
        )

    return errors
