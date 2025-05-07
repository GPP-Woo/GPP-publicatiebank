from time import time
from typing import Literal

from django.core.cache import caches
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from axes.helpers import get_client_ip_address


class ThrottleMixin:
    """
    A very simple throttling implementation with, hopefully, sane defaults.

    You can specifiy the amount of visits (throttle_visits) a view can get,
    for a specific period (in seconds) throttle_period.
    """

    # n visits per period (in seconds)
    throttle_visits = 100
    throttle_period = 60**2  # in seconds
    throttle_403 = True
    throttle_name = "default"

    # get and options should always be fast. By default
    # do not throttle them.
    throttle_methods: list[str] | Literal["all"] = [
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "trace",
    ]

    request: HttpRequest

    def get_throttle_cache(self):
        return caches["default"]

    def get_throttle_identifier(self) -> str:  # pragma: no cover
        user = getattr(self, "user_cache", self.request.user)
        return str(user.pk)

    def create_throttle_key(self):
        """
        :rtype string Use as key to save the last access
        """

        return (
            f"throttling_{self.get_throttle_identifier()}_"
            f"{self.throttle_name}_{self.get_throttle_window()}"
        )

    def get_throttle_window(self):
        """
        round down to the throttle_period, which is then used to create the key.
        """
        current_time = int(time())
        return current_time - (current_time % self.throttle_period)

    def get_visits_in_window(self):
        cache = self.get_throttle_cache()
        key = self.create_throttle_key()

        initial_visits = 1
        stored = cache.add(key, initial_visits, self.throttle_period)
        if stored:
            visits = initial_visits
        else:
            try:
                visits = cache.incr(key)
            except ValueError:  # pragma: no cover
                visits = initial_visits
        return visits

    def should_be_throttled(self):
        if self.throttle_methods == "all":  # pragma: no cover
            return True
        assert self.request.method is not None
        return self.request.method.lower() in self.throttle_methods

    def dispatch(self, request, *args, **kwargs):
        if self.throttle_403:  # pragma: no cover
            if (
                self.should_be_throttled()
                and self.get_visits_in_window() > self.throttle_visits
            ):
                raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)  # pyright: ignore


class IPThrottleMixin(ThrottleMixin):
    """
    Same behavior as ThrottleMixin except it limits the amount of tries
    per IP-address a user can access a certain view.
    """

    def get_throttle_identifier(self) -> str:
        ip_address = get_client_ip_address(self.request)
        assert ip_address is not None
        return ip_address
