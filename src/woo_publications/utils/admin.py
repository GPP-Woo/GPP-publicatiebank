from django.contrib.admin import DateFieldListFilter
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PastAndFutureDateFieldFilter(DateFieldListFilter):
    def _order_links(self):
        list_order = (
            _("Any date"),
            _("Today"),
            _("Past 7 days"),
            _("This month"),
            _("This year"),
            _("Last year"),
            _("No date"),
            _("Has date"),
        )

        self.links = tuple(
            sorted(self.links, key=lambda link: list_order.index(link[0]))
        )

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)

        now = timezone.now()

        if isinstance(field, models.DateTimeField):
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # field is a models.DateField
            today = now.date()

        last_year = today.replace(year=today.year - 1, month=1, day=1)

        self.links += (  # pyright: ignore[reportAttributeAccessIssue]
            (
                _("Last year"),
                {
                    self.lookup_kwarg_since: str(last_year),
                    self.lookup_kwarg_until: str(today.replace(month=1, day=1)),
                },
            ),
        )

        self._order_links()
