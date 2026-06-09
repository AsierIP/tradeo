from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

US_EQUITY_TZ = ZoneInfo("America/New_York")
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)


def is_us_equity_regular_session_open(now: datetime | None = None) -> bool:
    current = now or datetime.now(US_EQUITY_TZ)
    if current.tzinfo is None:
        current = current.replace(tzinfo=US_EQUITY_TZ)
    local = current.astimezone(US_EQUITY_TZ)
    if local.weekday() >= 5:
        return False
    if is_nyse_holiday(local.date()):
        return False
    current_time = local.time()
    return REGULAR_OPEN <= current_time < REGULAR_CLOSE


def market_session_status(now: datetime | None = None) -> dict[str, object]:
    current = now or datetime.now(US_EQUITY_TZ)
    local = current.astimezone(US_EQUITY_TZ) if current.tzinfo else current.replace(tzinfo=US_EQUITY_TZ)
    is_open = is_us_equity_regular_session_open(local)
    return {
        "market": "us_equities",
        "timezone": "America/New_York",
        "regular_session_open": is_open,
        "state": _session_state(local, is_open),
        "checked_at": local.isoformat(),
        "regular_hours": "09:30-16:00",
        "holiday": holiday_name(local.date()),
    }


def _session_state(local: datetime, is_open: bool) -> str:
    if is_open:
        return "regular_open"
    if is_nyse_holiday(local.date()):
        return "market_holiday"
    return "market_closed"


def is_nyse_holiday(day: date) -> bool:
    return holiday_name(day) is not None


def holiday_name(day: date) -> str | None:
    holidays = {
        _observed_fixed(day.year, 1, 1): "new_years_day",
        _observed_fixed(day.year + 1, 1, 1): "new_years_day",
        _nth_weekday(day.year, 1, 0, 3): "martin_luther_king_jr_day",
        _nth_weekday(day.year, 2, 0, 3): "washingtons_birthday",
        _good_friday(day.year): "good_friday",
        _last_weekday(day.year, 5, 0): "memorial_day",
        _observed_fixed(day.year, 6, 19): "juneteenth",
        _observed_fixed(day.year, 7, 4): "independence_day",
        _nth_weekday(day.year, 9, 0, 1): "labor_day",
        _nth_weekday(day.year, 11, 3, 4): "thanksgiving_day",
        _observed_fixed(day.year, 12, 25): "christmas_day",
    }
    return holidays.get(day)


def _observed_fixed(year: int, month: int, day: int) -> date:
    actual = date(year, month, day)
    if actual.weekday() == 5:
        return actual - timedelta(days=1)
    if actual.weekday() == 6:
        return actual + timedelta(days=1)
    return actual


def _nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    current = date(year, month, 1)
    days_until = (weekday - current.weekday()) % 7
    return current + timedelta(days=days_until + (nth - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    current = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def _good_friday(year: int) -> date:
    # Anonymous Gregorian algorithm; NYSE closes on Good Friday.
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    weekday_offset = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * weekday_offset) // 451
    month = (h + weekday_offset - 7 * m + 114) // 31
    day = ((h + weekday_offset - 7 * m + 114) % 31) + 1
    return date(year, month, day) - timedelta(days=2)
