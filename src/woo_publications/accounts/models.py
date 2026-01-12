import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_otp.plugins.otp_totp.models import TOTPDevice

from .managers import OrganisationMemberManager, OrganisationUnitManager, UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Use the built-in user model.
    """

    id: int

    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_("first name"), max_length=255, blank=True)
    last_name = models.CharField(_("last name"), max_length=255, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()
    totpdevice_set: ClassVar[models.Manager[TOTPDevice]]

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(
                fields=["email"], condition=~Q(email=""), name="filled_email_unique"
            )
        ]

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name


class OrganisationMember(models.Model):
    identifier = models.CharField(
        _("identifier"),
        help_text=_(
            "The system identifier that uniquely identifies the user performing "
            "the action."
        ),
        max_length=255,
        unique=True,
    )
    naam = models.CharField(
        _("naam"),
        help_text=_("The display name of the user."),
        max_length=255,
    )

    objects: ClassVar[OrganisationMemberManager] = OrganisationMemberManager()  # pyright: ignore[reportIncompatibleVariableOverride]

    class Meta:
        verbose_name = _("organisation member")
        verbose_name_plural = _("organisation members")
        indexes = [
            models.Index(fields=("identifier",)),
        ]

    def __str__(self):
        return f"{self.naam} - ({self.identifier})"


def uuid_slug() -> str:
    """
    Generated a stringified UUID to use as slug/identifier.
    """
    return str(uuid.uuid4())


class OrganisationUnit(models.Model):
    """
    A logical group of people that can perform a task.

    The organisation unit is an alternative owner role, as a counterpart to a single
    organisation member. Resources owned by an organisation unit can be managed by any
    member of that unit.
    """

    identifier = models.SlugField(
        _("identifier"),
        help_text=_(
            "The system identifier that uniquely identifies the organisation unit "
            "performing the action."
        ),
        max_length=255,
        default=uuid_slug,
        unique=True,
    )
    naam = models.CharField(
        _("naam"),
        help_text=_("The display name of the organisation unit."),
        max_length=255,
    )

    objects: ClassVar[OrganisationUnitManager] = OrganisationUnitManager()  # pyright: ignore[reportIncompatibleVariableOverride]

    class Meta:
        verbose_name = _("organisation unit")
        verbose_name_plural = _("organisation units")
        indexes = [
            models.Index(fields=("identifier",)),
        ]

    def __str__(self):
        return f"{self.naam} - ({self.identifier})"
