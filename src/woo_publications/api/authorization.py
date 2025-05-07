from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as _TokenAuthentication

from .models import Application


class TokenAuthentication(_TokenAuthentication):
    def authenticate_credentials(self, key):
        try:
            token = Application.objects.get(token=key)
        except Application.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed(_("Invalid token.")) from exc

        return (None, token)
