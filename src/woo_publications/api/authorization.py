from django.contrib.auth.models import AnonymousUser
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

        # Return an AnonymousUser rather than None: the Application token is not
        # tied to a user, but sessionprofile's middleware reads
        # ``request.user.is_authenticated`` on every response, which raises
        # ``AttributeError`` on a ``None`` user whenever a session profile exists
        # (i.e. while any admin session is active). AnonymousUser is falsy for
        # ``is_authenticated`` and keeps permissions (which key off ``request.auth``)
        # unchanged.
        return (AnonymousUser(), token)
