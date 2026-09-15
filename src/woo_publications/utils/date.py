import datetime

from workalendar.europe import Netherlands as DutchCalendar


def get_workday(date: datetime.date) -> datetime.date:
    """
    Get the first available workday for the given date.
    If the given date is on a workday it simply returns it,
    if it falls on a holiday or in the weekend then it checks and returns the next
    available workday.

    :arg date: A date object which we should base the first available workday on.
    """
    calendar = DutchCalendar()

    # inefficient way to check for next work day but since the
    # 'find_following_working_day' doesn't take holidays into account
    # this is the best next things:
    # https://workalendar.github.io/workalendar/advanced.html#find-the-following-working-day-after-a-date
    while not calendar.is_working_day(date):
        date += datetime.timedelta(days=1)

    return date
