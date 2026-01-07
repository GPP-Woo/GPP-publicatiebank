import factory
from factory.django import DjangoModelFactory

from ..models import OrganisationMember, OrganisationUnit, User


class UserFactory(DjangoModelFactory[User]):
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


class OrganisationMemberFactory(DjangoModelFactory[OrganisationMember]):
    identifier = factory.Sequence(lambda n: f"identifier-{n}")
    naam = factory.Faker("name")

    class Meta:  # pyright: ignore
        model = OrganisationMember


class OrganisationUnitFactory(DjangoModelFactory[OrganisationUnit]):
    identifier = factory.Sequence(lambda n: f"identifier-{n}")
    naam = factory.Faker("name")

    class Meta:  # pyright: ignore
        model = OrganisationUnit
