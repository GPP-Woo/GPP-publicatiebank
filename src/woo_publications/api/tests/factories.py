import factory

from ..constants import ApiOptions, PermissionOptions
from ..models import Application


class TokenAuthFactory(factory.django.DjangoModelFactory):
    permissions = []
    api_access = []

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

        application_api_access = factory.Trait(api_access=[ApiOptions.application])
        reuse_api_access = factory.Trait(api_access=[ApiOptions.reuse])
        full_api_access = factory.Trait(
            api_access=[
                ApiOptions.application,
                ApiOptions.reuse,
            ]
        )

    @factory.post_generation
    def generate_token(self, create, extracted, **kwargs):
        if not create:
            return

        self.raw_token = self.get_and_set_token()  # pyright: ignore[reportAttributeAccessIssue]
