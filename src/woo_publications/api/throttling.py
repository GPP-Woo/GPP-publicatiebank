from rest_framework.throttling import SimpleRateThrottle

from woo_publications.api.models import Application


class AnonRateThrottle(SimpleRateThrottle):
    scope = "anon"

    def get_cache_key(self, request, view):
        token = request.auth

        if isinstance(token, Application):
            return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ReuseRateThrottle(SimpleRateThrottle):
    scope = "reuse"

    def get_cache_key(self, request, view):
        token = request.auth

        if not isinstance(token, Application):
            return

        return self.cache_format % {
            "scope": self.scope,
            "ident": token.pk,
        }
