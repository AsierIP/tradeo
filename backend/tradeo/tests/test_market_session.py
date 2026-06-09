from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradeo.services.market_session import is_us_equity_regular_session_open, market_session_status


NY = ZoneInfo("America/New_York")


def test_us_equity_regular_session_is_open_during_weekday_rth() -> None:
    assert is_us_equity_regular_session_open(datetime(2026, 6, 9, 10, 0, tzinfo=NY)) is True


def test_us_equity_regular_session_is_closed_after_hours() -> None:
    assert is_us_equity_regular_session_open(datetime(2026, 6, 9, 17, 0, tzinfo=NY)) is False


def test_market_session_status_reports_closed_state() -> None:
    status = market_session_status(datetime(2026, 6, 13, 10, 0, tzinfo=NY))

    assert status["regular_session_open"] is False
    assert status["state"] == "market_closed"


def test_market_session_closes_on_nyse_holiday() -> None:
    status = market_session_status(datetime(2026, 6, 19, 10, 0, tzinfo=NY))

    assert status["regular_session_open"] is False
    assert status["state"] == "market_holiday"
    assert status["holiday"] == "juneteenth"
