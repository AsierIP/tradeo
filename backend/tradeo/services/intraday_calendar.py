from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from tradeo.services.market_session import holiday_name as rule_based_holiday_name

NYSE_TZ = ZoneInfo("America/New_York")
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
DEFAULT_EARLY_CLOSE = time(13, 0)

DEFAULT_NO_NEW_ENTRY_MINUTES = 30
DEFAULT_CANCEL_ENTRY_MINUTES = 20
DEFAULT_FORCE_FLAT_MINUTES = 15
DEFAULT_HARD_FLAT_MINUTES = 5

DEFAULT_CALENDAR_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "nyse_intraday_calendar.json"
)


class CalendarUnavailable(RuntimeError):
    """Raised when intraday cannot trust its market calendar."""


class TradingNotAllowed(RuntimeError):
    """Raised when an intraday action is outside the allowed session window."""


class IntradayTradingIntent(str, Enum):
    ENTRY = "ENTRY"
    CANCEL = "CANCEL"
    FLATTEN = "FLATTEN"
    RECONCILE = "RECONCILE"


@dataclass(frozen=True)
class IntradayCutoffs:
    no_new_entries_at: datetime
    cancel_entries_at: datetime
    force_flat_start_at: datetime
    hard_flat_deadline_at: datetime


@dataclass(frozen=True)
class IntradaySession:
    session_date: date
    market: str
    timezone: str
    calendar_available: bool
    is_open: bool
    status: str
    reason: str
    regular_open_at: datetime | None
    regular_close_at: datetime | None
    is_half_day: bool = False
    holiday_name: str | None = None
    cutoffs: IntradayCutoffs | None = None

    @property
    def no_new_entries_at(self) -> datetime | None:
        return self.cutoffs.no_new_entries_at if self.cutoffs else None

    @property
    def cancel_entries_at(self) -> datetime | None:
        return self.cutoffs.cancel_entries_at if self.cutoffs else None

    @property
    def force_flat_start_at(self) -> datetime | None:
        return self.cutoffs.force_flat_start_at if self.cutoffs else None

    @property
    def hard_flat_deadline_at(self) -> datetime | None:
        return self.cutoffs.hard_flat_deadline_at if self.cutoffs else None


class IntradayMarketCalendar:
    """NYSE intraday calendar with local fallback and fail-closed semantics."""

    def __init__(
        self,
        *,
        fallback_path: Path | str | None = DEFAULT_CALENDAR_PATH,
        market: str = "NYSE",
        timezone_name: str = "America/New_York",
        no_new_entry_minutes_before_close: int = DEFAULT_NO_NEW_ENTRY_MINUTES,
        cancel_entry_minutes_before_close: int = DEFAULT_CANCEL_ENTRY_MINUTES,
        force_flat_minutes_before_close: int = DEFAULT_FORCE_FLAT_MINUTES,
        hard_flat_minutes_before_close: int = DEFAULT_HARD_FLAT_MINUTES,
        require_fallback: bool = True,
    ) -> None:
        self.market = market
        self.timezone_name = timezone_name
        self.market_tz = ZoneInfo(timezone_name)
        self.no_new_entry_minutes_before_close = no_new_entry_minutes_before_close
        self.cancel_entry_minutes_before_close = cancel_entry_minutes_before_close
        self.force_flat_minutes_before_close = force_flat_minutes_before_close
        self.hard_flat_minutes_before_close = hard_flat_minutes_before_close
        self.require_fallback = require_fallback
        self.fallback_path = Path(fallback_path) if fallback_path is not None else None
        self._calendar_error: str | None = None
        self._payload = self._load_payload()

    @property
    def calendar_available(self) -> bool:
        return self._calendar_error is None

    @property
    def calendar_error(self) -> str | None:
        return self._calendar_error

    def session_for(self, value: date | datetime | None = None) -> IntradaySession:
        local = self._coerce_datetime(value) if value is not None else datetime.now(self.market_tz)
        day = local.date()
        if not self.calendar_available:
            return self._closed_session(
                day,
                status="calendar_unavailable",
                reason=self._calendar_error or "calendar_unavailable",
                calendar_available=False,
            )
        if day.weekday() >= 5:
            return self._closed_session(day, status="weekend", reason="weekend")
        holiday = self._holiday_name(day)
        if holiday:
            return self._closed_session(
                day,
                status="holiday",
                reason=f"holiday:{holiday}",
                holiday_name=holiday,
            )

        open_time = self._configured_time(day, "opens", REGULAR_OPEN)
        close_time = self._configured_time(day, "closes", REGULAR_CLOSE)
        half_day_name = self._half_day_name(day)
        if half_day_name and close_time == REGULAR_CLOSE:
            close_time = DEFAULT_EARLY_CLOSE

        open_at = datetime.combine(day, open_time, self.market_tz)
        close_at = datetime.combine(day, close_time, self.market_tz)
        cutoffs = self._cutoffs(close_at)
        is_half_day = bool(half_day_name) or close_at.time() < REGULAR_CLOSE
        return IntradaySession(
            session_date=day,
            market=self.market,
            timezone=self.timezone_name,
            calendar_available=True,
            is_open=True,
            status="half_day" if is_half_day else "regular",
            reason=half_day_name or "regular_session",
            regular_open_at=open_at,
            regular_close_at=close_at,
            is_half_day=is_half_day,
            holiday_name=None,
            cutoffs=cutoffs,
        )

    def assert_trading_allowed(
        self,
        now: datetime | None = None,
        intent: IntradayTradingIntent | str = IntradayTradingIntent.ENTRY,
    ) -> IntradaySession:
        action = self._coerce_intent(intent)
        local = self._coerce_datetime(now) if now is not None else datetime.now(self.market_tz)
        session = self.session_for(local)
        if not session.calendar_available:
            raise CalendarUnavailable(session.reason)
        if action == IntradayTradingIntent.RECONCILE:
            return session
        if not session.is_open or not session.regular_open_at or not session.regular_close_at:
            raise TradingNotAllowed(session.reason)
        if local < session.regular_open_at:
            raise TradingNotAllowed("before_regular_open")
        if local >= session.regular_close_at:
            raise TradingNotAllowed("after_regular_close")
        if action == IntradayTradingIntent.ENTRY:
            assert session.no_new_entries_at is not None
            if local >= session.no_new_entries_at:
                raise TradingNotAllowed("no_new_entries_cutoff")
            return session
        assert session.hard_flat_deadline_at is not None
        if local >= session.hard_flat_deadline_at:
            raise TradingNotAllowed("hard_flat_deadline_passed")
        return session

    def _load_payload(self) -> dict[str, Any]:
        if self.fallback_path is None:
            if self.require_fallback:
                self._calendar_error = "calendar_fallback_path_missing"
                return {}
            return {}
        try:
            payload = json.loads(self.fallback_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if self.require_fallback:
                self._calendar_error = f"calendar_fallback_unavailable:{type(exc).__name__}"
            return {}
        if not isinstance(payload, dict):
            if self.require_fallback:
                self._calendar_error = "calendar_fallback_invalid"
            return {}
        return payload

    def _closed_session(
        self,
        day: date,
        *,
        status: str,
        reason: str,
        calendar_available: bool = True,
        holiday_name: str | None = None,
    ) -> IntradaySession:
        return IntradaySession(
            session_date=day,
            market=self.market,
            timezone=self.timezone_name,
            calendar_available=calendar_available,
            is_open=False,
            status=status,
            reason=reason,
            regular_open_at=None,
            regular_close_at=None,
            holiday_name=holiday_name,
        )

    def _cutoffs(self, close_at: datetime) -> IntradayCutoffs:
        return IntradayCutoffs(
            no_new_entries_at=close_at - timedelta(minutes=self.no_new_entry_minutes_before_close),
            cancel_entries_at=close_at - timedelta(minutes=self.cancel_entry_minutes_before_close),
            force_flat_start_at=close_at - timedelta(minutes=self.force_flat_minutes_before_close),
            hard_flat_deadline_at=close_at - timedelta(minutes=self.hard_flat_minutes_before_close),
        )

    def _holiday_name(self, day: date) -> str | None:
        configured = self._lookup_day("holidays", day)
        if configured is not None:
            return str(configured)
        closures = self._lookup_day("closures", day)
        if closures is not None:
            return str(closures.get("name") if isinstance(closures, dict) else closures)
        return rule_based_holiday_name(day)

    def _half_day_name(self, day: date) -> str | None:
        value = self._lookup_day("half_days", day)
        if value is None:
            value = self._lookup_day("special_closes", day)
        if value is None:
            return None
        if isinstance(value, dict):
            return str(value.get("name") or "early_close")
        return str(value)

    def _configured_time(self, day: date, key: str, default: time) -> time:
        value = self._lookup_day(key, day)
        if value is None and key == "closes":
            value = self._lookup_day("special_closes", day)
            if value is None:
                value = self._lookup_day("half_days", day)
        if isinstance(value, dict):
            raw = value.get("time") or value.get("close") or value.get("open")
        else:
            raw = value
        if raw is None:
            return default
        return self._parse_time(str(raw), default)

    def _lookup_day(self, section: str, day: date) -> Any:
        raw_section = self._payload.get(section, {})
        if not isinstance(raw_section, dict):
            return None
        return raw_section.get(day.isoformat())

    @staticmethod
    def _parse_time(value: str, default: time) -> time:
        try:
            hour, minute = value.split(":", maxsplit=1)
            return time(int(hour), int(minute))
        except (ValueError, TypeError):
            return default

    def _coerce_datetime(self, value: date | datetime | None) -> datetime:
        if value is None:
            return datetime.now(self.market_tz)
        if isinstance(value, datetime):
            return (
                value.replace(tzinfo=self.market_tz)
                if value.tzinfo is None
                else value.astimezone(self.market_tz)
            )
        return datetime.combine(value, time(12, 0), self.market_tz)

    @staticmethod
    def _coerce_intent(intent: IntradayTradingIntent | str) -> IntradayTradingIntent:
        if isinstance(intent, IntradayTradingIntent):
            return intent
        try:
            return IntradayTradingIntent[str(intent).strip().upper()]
        except KeyError as exc:
            raise ValueError(f"unsupported intraday trading intent: {intent}") from exc
