from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import BaseUserManager
from django.db import models, transaction

if TYPE_CHECKING:
    from .models import OrganisationMember, OrganisationUnit


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        if not username:  # pragma: no cover
            raise ValueError("The given username must be set")
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:  # pragma: no cover
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:  # pragma: no cover
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, email, password, **extra_fields)


class OrganisationMemberManager(models.Manager["OrganisationMember"]):
    @transaction.atomic
    def get_and_sync(self, identifier: str, naam: str) -> OrganisationMember:
        obj, _ = self.update_or_create(identifier=identifier, defaults={"naam": naam})
        return obj


class OrganisationUnitManager(models.Manager["OrganisationUnit"]):
    @transaction.atomic
    def get_and_sync(self, identifier: str, naam: str) -> OrganisationUnit:
        obj, _ = self.update_or_create(identifier=identifier, defaults={"naam": naam})
        return obj
