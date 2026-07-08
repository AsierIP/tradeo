from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from tradeo.research.intraday_vwap_features import build_intraday_vwap_features
from tradeo.services.technical_indicators import normalize_ohlcv

SESSION_FILTER_CHOICES = frozenset({"none", "open", "mid", "close", "no_close"})
COST_FILTER_CHOICES = frozenset({"none", "low_cost"})
BENCHMARK_REGIME_FILTER_CHOICES = frozenset(
    {
        "none",
        "spy_qqq_positive",
        "spy_qqq_negative",
        "spy_positive",
        "qqq_positive",
        "spy_qqq_risk_off",
    }
)
DEFAULT_LOW_COST_MAX_EXECUTION_COST_R = 0.15
DEFAULT_BENCHMARK_SYMBOLS = ("SPY", "QQQ")
MARKET_TIMEZONE = "America/New_York"

_NY = ZoneInfo(MARKET_TIMEZONE)


@dataclass(frozen=True, slots=True)
class IntradayContextFilterSpec:
    session_filter: str = "none"
    cost_filter: str = "none"
    max_execution_cost_r: float | None = None
    benchmark_regime_filter: str = "none"
    benchmark_symbols: tuple[str, ...] = DEFAULT_BENCHMARK_SYMBOLS

    @property
    def session_enabled(self) -> bool:
        return self.session_filter != "none"

    @property
    def cost_enabled(self) -> bool:
        return self.cost_filter != "none"

    @property
    def benchmark_enabled(self) -> bool:
        return self.benchmark_regime_filter != "none"


def normalize_context_filter_spec(
    *,
    session_filter: str | None = None,
    cost_filter: str | None = None,
    max_execution_cost_r: float | str | None = None,
    benchmark_regime_filter: str | None = None,
    benchmark_symbols: str | list[str] | tuple[str, ...] | None = None,
) -> IntradayContextFilterSpec:
    session = _normalize_session_filter(session_filter)
    cost = _normalize_cost_filter(cost_filter)
    max_cost = _optional_float(max_execution_cost_r)
    if cost == "low_cost" and max_cost is None:
        max_cost = DEFAULT_LOW_COST_MAX_EXECUTION_COST_R
    benchmark_filter = _normalize_benchmark_regime_filter(benchmark_regime_filter)
    benchmark_symbol_tuple = _normalize_benchmark_symbols(benchmark_symbols)
    return IntradayContextFilterSpec(
        session_filter=session,
        cost_filter=cost,
        max_execution_cost_r=max_cost,
        benchmark_regime_filter=benchmark_filter,
        benchmark_symbols=benchmark_symbol_tuple,
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


def build_benchmark_regime_frames(
    benchmark_frames: dict[str, pd.DataFrame] | None,
    spec: IntradayContextFilterSpec,
) -> dict[str, pd.DataFrame]:
    if not spec.benchmark_enabled or not benchmark_frames:
        return {}
    out: dict[str, pd.DataFrame] = {}
    lower_map = {str(key).upper(): value for key, value in benchmark_frames.items()}
    for symbol in spec.benchmark_symbols:
        frame = lower_map.get(symbol.upper())
        if frame is None or frame.empty:
            continue
        normalized = normalize_ohlcv(frame)
        features = build_intraday_vwap_features(
            normalized,
            price_mode="close",
            slope_lookback=1,
            session_tz=MARKET_TIMEZONE,
        ).frame
        out[symbol.upper()] = features.sort_index()
    return out


def benchmark_regime_filter_passes(
    timestamp: Any,
    spec: IntradayContextFilterSpec,
    benchmark_regime_frames: dict[str, pd.DataFrame] | None,
) -> tuple[bool, bool, dict[str, Any]]:
    if not spec.benchmark_enabled:
        return True, False, {}
    states: dict[str, str] = {}
    for symbol in spec.benchmark_symbols:
        row = _benchmark_row_at_or_before(timestamp, (benchmark_regime_frames or {}).get(symbol.upper()))
        if row is None:
            return False, True, {"benchmark_regime_states": states}
        state = _benchmark_state(row)
        states[symbol.upper()] = state
    required = _required_benchmark_states(spec.benchmark_regime_filter)
    passed = all(states.get(symbol) == state for symbol, state in required.items())
    return passed, False, {"benchmark_regime_states": states}


def benchmark_context_filter_payload(spec: IntradayContextFilterSpec) -> dict[str, Any]:
    return {
        "benchmark_regime_filter": spec.benchmark_regime_filter,
        "benchmark_symbols": list(spec.benchmark_symbols),
    }


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
        "benchmark_regime_filter": spec.benchmark_regime_filter,
        "benchmark_symbols": list(spec.benchmark_symbols),
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


def _normalize_benchmark_regime_filter(value: str | None) -> str:
    normalized = str(value or "none").strip().lower() or "none"
    if normalized not in BENCHMARK_REGIME_FILTER_CHOICES:
        raise ValueError(
            "benchmark_regime_filter must be one of: "
            + ", ".join(sorted(BENCHMARK_REGIME_FILTER_CHOICES))
        )
    return normalized


def _normalize_benchmark_symbols(value: str | list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    if value is None or value == "":
        return DEFAULT_BENCHMARK_SYMBOLS
    if isinstance(value, str):
        raw_items = value.split(",")
    else:
        raw_items = list(value)
    symbols = tuple(dict.fromkeys(str(item).strip().upper() for item in raw_items if str(item).strip()))
    return symbols or DEFAULT_BENCHMARK_SYMBOLS


def _optional_float(value: float | str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _benchmark_row_at_or_before(timestamp: Any, frame: pd.DataFrame | None) -> pd.Series | None:
    if frame is None or frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        return None
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        ts = ts.tz_localize(_NY)
    else:
        ts = ts.tz_convert(_NY)
    index = frame.index
    if index.tz is None:
        ts = ts.tz_localize(None)
    else:
        ts = ts.tz_convert(index.tz)
    pos = index.searchsorted(ts, side="right") - 1
    if pos < 0:
        return None
    return frame.iloc[int(pos)]


def _benchmark_state(row: pd.Series) -> str:
    close = _optional_float(row.get("close"))
    vwap = _optional_float(row.get("vwap"))
    slope = _optional_float(row.get("vwap_slope_bps"))
    if close is None or vwap is None or slope is None:
        return "missing"
    if close >= vwap and slope >= 0:
        return "positive"
    if close <= vwap and slope <= 0:
        return "negative"
    return "neutral"


def _required_benchmark_states(filter_name: str) -> dict[str, str]:
    if filter_name == "spy_qqq_positive":
        return {"SPY": "positive", "QQQ": "positive"}
    if filter_name == "spy_qqq_negative":
        return {"SPY": "negative", "QQQ": "negative"}
    if filter_name == "spy_positive":
        return {"SPY": "positive"}
    if filter_name == "qqq_positive":
        return {"QQQ": "positive"}
    if filter_name == "spy_qqq_risk_off":
        return {"SPY": "negative", "QQQ": "negative"}
    return {}
