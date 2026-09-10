import datetime

from django.test import SimpleTestCase

from woo_publications.utils.date import get_workday


class GetWorkdaySimpleTestCase(SimpleTestCase):
    def test_weekday_does_not_alter(self):
        date = datetime.date(year=2012, month=12, day=21)
        workday_date = get_workday(date)

        self.assertEqual(workday_date, date)

    def test_weekend_days_skips_to_next_work_date(self):
        saturday = datetime.date(year=2025, month=5, day=24)
        sunday = datetime.date(year=2025, month=5, day=25)
        monday = datetime.date(year=2025, month=5, day=26)

        self.assertEqual(get_workday(saturday), monday)
        self.assertEqual(get_workday(sunday), monday)

    def test_holiday_skips_to_next_work_date(self):
        # this is a monday
        kingsday = datetime.date(year=2026, month=4, day=27)
        tuesday = datetime.date(year=2026, month=4, day=28)

        self.assertEqual(get_workday(kingsday), tuesday)
