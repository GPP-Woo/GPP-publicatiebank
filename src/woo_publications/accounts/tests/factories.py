from django.contrib.auth import get_user_model

import factory
from factory.django import DjangoModelFactory

from ..models import OrganisationMember

User = get_user_model()


class UserFactory(DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "password")

    class Meta:  # pyright: ignore
        model = User

    class Params:
        superuser = factory.Trait(
            is_staff=True,
            is_superuser=True,
        )


class OrganisationMemberFactory(DjangoModelFactory):
    identifier = factory.Sequence(lambda n: f"identifier-{n}")
    naam = factory.Faker("name")

    class Meta:  # pyright: ignore
        model = OrganisationMember
