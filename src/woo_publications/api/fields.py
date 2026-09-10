import datetime

from rest_framework import serializers

from woo_publications.utils.date import get_workday


class WorkDateField(serializers.DateField):
    def to_internal_value(self, data):
        date = super().to_internal_value(data)
        assert isinstance(date, datetime.date)

        return get_workday(date)
