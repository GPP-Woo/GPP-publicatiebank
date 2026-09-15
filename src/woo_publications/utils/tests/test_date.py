import datetime

from django.test import SimpleTestCase

from dateutil import easter
from hypothesis import example, given
from hypothesis.strategies import dates

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

    @given(
        dates(
            min_value=datetime.date(2026, 1, 1), max_value=datetime.date(2119, 12, 31)
        )
    )
    @example(datetime.date(2038, 4, 23))
    def test_workday(self, today: datetime.date):
        """
        Artikel 3 of Algemene Termijnwet:

        https://wetten.overheid.nl/BWBR0002448/2010-10-10/#Artikel3

         1. Algemeen erkende feestdagen in de zin van deze wet zijn:
         de Nieuwjaarsdag, de Christelijke tweede Paas- en Pinksterdag,
         de beide Kerstdagen, de Hemelvaartsdag,
         de dag waarop de verjaardag van de Koning wordt gevierd en de vijfde mei.
         2. Voor de toepassing van deze wet wordt de Goede Vrijdag met de in het vorige
         lid genoemde dagen gelijkgesteld.
         3. Wij kunnen bepaalde dagen voor de toepassing van deze wet met de in
         het eerste lid genoemde gelijkstellen. Ons besluit wordt in de
         Nederlandse Staatscourant openbaar gemaakt.
        """
        day = get_workday(today)

        # 1. de Nieuwjaarsdag
        newyear = datetime.date(day.year, 1, 1)

        # 2. Goede Vrijdag, Eerste en Tweede Paasdag
        paas1 = easter.easter(day.year)
        paas2 = paas1 + datetime.timedelta(days=1)
        goede_vrijdag = paas1 - datetime.timedelta(days=2)

        # 3. Hemelvaartsdag (39 dagen na Pasen / 6e donderdag na Pasen)
        hemelvaart = paas1 + datetime.timedelta(days=39)

        # 4. Eerste en Tweede Pinksterdag (49 en 50 dagen na Pasen)
        pinkster1 = paas1 + datetime.timedelta(days=49)
        pinkster2 = paas1 + datetime.timedelta(days=50)

        # 5. Koningsdag (27 april, of 26 april als 27 april op een zondag valt)
        koningsdag = (
            datetime.date(day.year, 4, 26)
            if datetime.date(day.year, 4, 27).weekday() == 6
            else datetime.date(day.year, 4, 27)
        )

        # 6. Bevrijdingsdag (5 mei)
        bevrijdingsdag = datetime.date(day.year, 5, 5)

        # 7. De beide Kerstdagen (25 en 26 december)
        kerst1 = datetime.date(day.year, 12, 25)
        kerst2 = datetime.date(day.year, 12, 26)

        # Combine all legally designated holidays
        holidays = {
            newyear,
            goede_vrijdag,
            paas1,
            paas2,
            hemelvaart,
            pinkster1,
            pinkster2,
            koningsdag,
            bevrijdingsdag,
            kerst1,
            kerst2,
        }

        # If 'day' was successfully shifted by 0 working days, it cannot be a
        # weekend or a legal holiday
        should_be_same = today.weekday() < 5 and today not in holidays
        assert (today == day) == should_be_same
        assert day.weekday() < 5
        assert day not in holidays

        # at most 5 days: from Goede Vrijdag till 2e Paasdag
        assert day - today <= datetime.timedelta(days=5)
