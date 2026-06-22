from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tradeo.services.intraday_calendar import (
    CalendarUnavailable,
    IntradayMarketCalendar,
    TradingNotAllowed,
)


NY = ZoneInfo("America/New_York")


def _calendar_file(tmp_path: Path) -> Path:
    path = tmp_path / "nyse.json"
    path.write_text(
        json.dumps(
            {
                "holidays": {"2026-01-01": "New Year's Day"},
                "half_days": {"2026-11-27": {"name": "Day after Thanksgiving", "time": "13:00"}},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_intraday_calendar_regular_half_day_weekend_and_holiday(tmp_path: Path) -> None:
    calendar = IntradayMarketCalendar(fallback_path=_calendar_file(tmp_path))

    regular = calendar.session_for(datetime(2026, 6, 22, 10, 0, tzinfo=NY))
    assert regular.status == "regular"
    assert regular.regular_close_at.hour == 16
    assert regular.no_new_entries_at.hour == 15
    assert regular.no_new_entries_at.minute == 30

    half_day = calendar.session_for(datetime(2026, 11, 27, 10, 0, tzinfo=NY))
    assert half_day.status == "half_day"
    assert half_day.regular_close_at.hour == 13
    assert half_day.no_new_entries_at.hour == 12
    assert half_day.no_new_entries_at.minute == 30

    weekend = calendar.session_for(datetime(2026, 6, 27, 10, 0, tzinfo=NY))
    assert weekend.is_open is False
    assert weekend.status == "weekend"

    holiday = calendar.session_for(datetime(2026, 1, 1, 10, 0, tzinfo=NY))
    assert holiday.is_open is False
    assert holiday.status == "holiday"


def test_intraday_calendar_blocks_entries_after_cutoff(tmp_path: Path) -> None:
    calendar = IntradayMarketCalendar(fallback_path=_calendar_file(tmp_path))

    with pytest.raises(TradingNotAllowed, match="no_new_entries_cutoff"):
        calendar.assert_trading_allowed(datetime(2026, 6, 22, 15, 35, tzinfo=NY), "ENTRY")

    assert calendar.assert_trading_allowed(datetime(2026, 6, 22, 15, 35, tzinfo=NY), "CANCEL")


def test_intraday_calendar_fail_closed_without_fallback(tmp_path: Path) -> None:
    calendar = IntradayMarketCalendar(fallback_path=tmp_path / "missing.json")

    session = calendar.session_for(datetime(2026, 6, 22, 10, 0, tzinfo=NY))
    assert session.calendar_available is False
    assert session.is_open is False
    with pytest.raises(CalendarUnavailable):
        calendar.assert_trading_allowed(datetime(2026, 6, 22, 10, 0, tzinfo=NY), "ENTRY")
