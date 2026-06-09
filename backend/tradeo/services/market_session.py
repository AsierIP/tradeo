from __future__ import annotations

from datetime import datetime, time
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
        "state": "regular_open" if is_open else "market_closed",
        "checked_at": local.isoformat(),
        "regular_hours": "09:30-16:00",
    }
