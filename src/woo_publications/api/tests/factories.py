import factory

from ..constants import PermissionOptions
from ..models import Application


class TokenAuthFactory(factory.django.DjangoModelFactory):
    permissions = []

    class Meta:  # pyright: ignore
        model = Application

    class Params:
        read_permission = factory.Trait(permissions=[PermissionOptions.read])
        write_permission = factory.Trait(permissions=[PermissionOptions.write])
        read_write_permission = factory.Trait(
            permissions=[
                PermissionOptions.read,
                PermissionOptions.write,
            ]
        )

    @factory.post_generation
    def generate_token(self, create, extracted, **kwargs):
        if not create:
            return

        self.raw_token = self.get_and_set_token()  # pyright: ignore[reportAttributeAccessIssue]
