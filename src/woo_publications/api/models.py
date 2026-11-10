from hashlib import sha256
from secrets import token_hex
from typing import Literal, TypedDict

from django.db import models
from django.utils.translation import gettext_lazy as _

from django_jsonform.models.fields import ArrayField
from django_stubs_ext import StrOrPromise

from .constants import ApiOptions, PermissionOptions


class ChoiceType(TypedDict):
    title: StrOrPromise
    value: StrOrPromise


class ItemsType(TypedDict):
    type: Literal["string"]
    choices: list[ChoiceType]


class SchemaType(TypedDict):
    type: Literal["list"]
    items: ItemsType


def schema(choices: list[tuple[str, StrOrPromise]]) -> SchemaType:
    return {
        "type": "list",
        "items": {
            "type": "string",
            "choices": [{"title": label, "value": value} for value, label in choices],
        },
    }


def generate_token() -> str:
    return token_hex(20)


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


class Application(models.Model):  # noqa: DJ008
    token = models.CharField(_("token"), max_length=64)
    permissions = ArrayField(
        models.CharField(max_length=20, choices=PermissionOptions.choices),
        verbose_name=_("permissions"),
        help_text=_("The permissions this API token has access to."),
        schema=schema(choices=PermissionOptions.choices),
        blank=True,
        default=list,
    )
    api_access = ArrayField(
        models.CharField(max_length=20, choices=ApiOptions.choices),
        verbose_name=_("API access"),
        help_text=_("The APIs this token has access to."),
        schema=schema(choices=ApiOptions.choices),
        blank=True,
        default=list,
    )
    contact_person = models.CharField(
        _("contact person"),
        max_length=200,
        help_text=_(
            "Name of the person to contact about this application and the associated "
            "credentials."
        ),
        blank=True,
        db_collation="nl-NL-x-icu",
    )
    email = models.EmailField(
        _("email"),
        help_text=_(
            "Email of the person to contact about this application and the associated "
            "credentials."
        ),
        blank=True,
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length=128,
        help_text=_(
            "Phonenumber of the person contact about this application and the "
            "associated credentials."
        ),
        blank=True,
    )
    expire_date = models.DateField(
        _("expire date"),
        help_text=_("The date when the token will no longer be available."),
        blank=True,
        null=True,
    )
    last_modified = models.DateTimeField(
        _("last modified"),
        auto_now=True,
        help_text=_("Last date when the token was modified"),
    )
    created = models.DateTimeField(
        _("created"), auto_now_add=True, help_text=_("Date when the token was created")
    )
    viewed_token_at = models.DateTimeField(
        _("token viewed at"),
        help_text=_("Date when the token was viewed in the admin."),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("application API key")
        verbose_name_plural = _("application API keys")
        constraints = [
            models.UniqueConstraint(
                fields=["token"],
                condition=~models.Q(token=""),
                name="unique_token",
                violation_error_message="The value of 'token' has to be unique.",
            )
        ]

    def get_and_set_token(self) -> str:
        token = generate_token()
        self.token = hash_token(token)
        return token
