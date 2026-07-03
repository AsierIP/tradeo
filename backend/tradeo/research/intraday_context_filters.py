from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

SESSION_FILTER_CHOICES = frozenset({"none", "open", "mid", "close", "no_close"})
COST_FILTER_CHOICES = frozenset({"none", "low_cost"})
DEFAULT_LOW_COST_MAX_EXECUTION_COST_R = 0.15
MARKET_TIMEZONE = "America/New_York"

_NY = ZoneInfo(MARKET_TIMEZONE)


@dataclass(frozen=True, slots=True)
class IntradayContextFilterSpec:
    session_filter: str = "none"
    cost_filter: str = "none"
    max_execution_cost_r: float | None = None

    @property
    def session_enabled(self) -> bool:
        return self.session_filter != "none"

    @property
    def cost_enabled(self) -> bool:
        return self.cost_filter != "none"


def normalize_context_filter_spec(
    *,
    session_filter: str | None = None,
    cost_filter: str | None = None,
    max_execution_cost_r: float | str | None = None,
) -> IntradayContextFilterSpec:
    session = _normalize_session_filter(session_filter)
    cost = _normalize_cost_filter(cost_filter)
    max_cost = _optional_float(max_execution_cost_r)
    if cost == "low_cost" and max_cost is None:
        max_cost = DEFAULT_LOW_COST_MAX_EXECUTION_COST_R
    return IntradayContextFilterSpec(
        session_filter=session,
        cost_filter=cost,
        max_execution_cost_r=max_cost,
    )


def session_filter_passes(timestamp: Any, spec: IntradayContextFilterSpec) -> bool:
    if not spec.session_enabled:
        return True
    local_time = timestamp_to_market_time(timestamp)
    if spec.session_filter == "open":
        return time(9, 30) <= local_time < time(10, 30)
    if spec.session_filter == "mid":
        return time(10, 30) <= local_time < time(15, 0)
    if spec.session_filter == "close":
        return time(15, 0) <= local_time < time(16, 0)
    if spec.session_filter == "no_close":
        return not (time(15, 0) <= local_time < time(16, 0))
    return True


def session_bucket(timestamp: Any) -> str:
    local_time = timestamp_to_market_time(timestamp)
    if time(9, 30) <= local_time < time(10, 30):
        return "open"
    if time(10, 30) <= local_time < time(15, 0):
        return "mid"
    if time(15, 0) <= local_time < time(16, 0):
        return "close"
    return "outside_regular"


def cost_filter_passes(execution_cost_r: float, spec: IntradayContextFilterSpec) -> bool:
    if not spec.cost_enabled:
        return True
    if spec.max_execution_cost_r is None:
        return True
    return float(execution_cost_r) <= float(spec.max_execution_cost_r)


def timestamp_to_market_time(timestamp: Any) -> time:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize(_NY)
    else:
        ts = ts.tz_convert(_NY)
    return ts.time()


def timestamp_timezone_assumption_for_index(index: Any) -> str | None:
    return (
        MARKET_TIMEZONE
        if isinstance(index, pd.DatetimeIndex) and index.tz is None
        else None
    )


def context_filter_payload(spec: IntradayContextFilterSpec) -> dict[str, Any]:
    return {
        "session_filter": spec.session_filter,
        "cost_filter": spec.cost_filter,
        "max_execution_cost_r": spec.max_execution_cost_r,
    }


def _normalize_session_filter(value: str | None) -> str:
    normalized = str(value or "none").strip().lower() or "none"
    aliases = {
        "mid_session": "mid",
        "middle": "mid",
        "opening": "open",
        "closing": "close",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SESSION_FILTER_CHOICES:
        raise ValueError(
            "session_filter must be one of: " + ", ".join(sorted(SESSION_FILTER_CHOICES))
        )
    return normalized


def _normalize_cost_filter(value: str | None) -> str:
    normalized = str(value or "none").strip().lower() or "none"
    if normalized not in COST_FILTER_CHOICES:
        raise ValueError("cost_filter must be one of: " + ", ".join(sorted(COST_FILTER_CHOICES)))
    return normalized


def _optional_float(value: float | str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)
