from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
import math
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from tradeo.services.technical_indicators import validate_ohlcv

CONTRACT_VERSION = "intraday-features-v1"
NY_TZ = ZoneInfo("America/New_York")
REGULAR_OPEN = time(9, 30)


@dataclass(frozen=True, slots=True)
class IntradayFeatureConfig:
    opening_range_minutes: int = 15
    atr_window: int = 14
    medium_liquidity_dollar_volume: float = 250_000.0
    high_liquidity_dollar_volume: float = 1_000_000.0
    tight_spread_bps: float = 25.0
    wide_spread_bps: float = 75.0


@dataclass(frozen=True, slots=True)
class IntradayFeatureSet:
    symbol: str
    timeframe: str
    contract_version: str
    frame: pd.DataFrame
    feature_columns: tuple[str, ...]

    def to_records(self) -> list[dict[str, Any]]:
        return self.frame.reset_index().to_dict(orient="records")


class IntradayFeatureBuilder:
    """Build deterministic, closed-bar intraday features from OHLCV bars."""

    def __init__(self, config: IntradayFeatureConfig | None = None) -> None:
        self.config = config or IntradayFeatureConfig()

    def build(
        self,
        bars: pd.DataFrame,
        *,
        symbol: str,
        previous_close: float,
        minute_volume_baseline: Mapping[int | str, float] | pd.Series | pd.DataFrame,
        timeframe: str = "5m",
        session_open: pd.Timestamp | str | None = None,
        session_close: pd.Timestamp | str | None = None,
    ) -> IntradayFeatureSet:
        if previous_close <= 0 or not math.isfinite(float(previous_close)):
            raise ValueError("previous_close must be a finite positive number")
        df = _normalize_bars(bars)
        if df.empty:
            raise ValueError("intraday feature bars must not be empty")

        open_at = _session_timestamp(df.index[0], session_open, REGULAR_OPEN)
        close_at = _session_timestamp(df.index[0], session_close, time(16, 0))
        minute_baseline = _coerce_minute_baseline(minute_volume_baseline)

        elapsed_minutes = _elapsed_minutes(df.index, open_at)
        baseline_volume = pd.Series(
            [
                _baseline_for_minute(minute_baseline, minute)
                for minute in elapsed_minutes.to_numpy(dtype=int)
            ],
            index=df.index,
            dtype=float,
        )
        if (baseline_volume <= 0).any() or not np.isfinite(baseline_volume.to_numpy()).all():
            raise ValueError("minute RVOL baseline must be finite and positive for every bar")

        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        cumulative_volume = df["volume"].cumsum()
        if (cumulative_volume <= 0).any():
            raise ValueError("cumulative intraday volume must be positive for VWAP")
        vwap = (typical_price * df["volume"]).cumsum() / cumulative_volume
        distance_to_vwap = df["close"] / vwap - 1.0

        opening_range = _opening_range(df, open_at, self.config.opening_range_minutes)
        true_range = _true_range(df)
        atr = true_range.rolling(window=self.config.atr_window, min_periods=1).mean()
        spread_proxy_bps = _spread_proxy_bps(df)
        dollar_volume = df["close"] * df["volume"]
        rvol = df["volume"] / baseline_volume
        gap_pct = (float(df["open"].iloc[0]) / float(previous_close) - 1.0) * 100.0

        features = pd.DataFrame(index=df.index)
        features["vwap"] = vwap
        features["distance_to_vwap"] = distance_to_vwap
        features["opening_range_high"] = opening_range["high"]
        features["opening_range_low"] = opening_range["low"]
        features["opening_range_pct"] = (
            (opening_range["high"] - opening_range["low"]) / df["close"]
        )
        features["gap_pct"] = gap_pct
        features["rvol"] = rvol
        features["rvol_baseline_volume"] = baseline_volume
        features["atr"] = atr
        features["spread_proxy_bps"] = spread_proxy_bps
        features["dollar_volume"] = dollar_volume
        features["minute_of_session"] = elapsed_minutes
        features["session_bucket"] = [
            _session_bucket(ts, open_at, close_at) for ts in df.index
        ]
        features["liquidity_bucket"] = [
            _liquidity_bucket(
                dv,
                spread,
                medium_dollar=self.config.medium_liquidity_dollar_volume,
                high_dollar=self.config.high_liquidity_dollar_volume,
                tight_spread=self.config.tight_spread_bps,
                wide_spread=self.config.wide_spread_bps,
            )
            for dv, spread in zip(dollar_volume, spread_proxy_bps, strict=True)
        ]
        features["contract_version"] = CONTRACT_VERSION

        numeric_columns = tuple(
            column
            for column in features.columns
            if pd.api.types.is_numeric_dtype(features[column])
        )
        _reject_non_finite(features, numeric_columns)

        return IntradayFeatureSet(
            symbol=symbol.upper().strip(),
            timeframe=timeframe,
            contract_version=CONTRACT_VERSION,
            frame=features,
            feature_columns=numeric_columns,
        )


def _normalize_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("intraday features require a DatetimeIndex")
    df = bars.copy()
    df.columns = [str(column).lower().replace(" ", "_") for column in df.columns]
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"intraday bars missing required columns: {missing}")
    df = df[required + [column for column in ("bid", "ask") if column in df.columns]]
    for column in required + [column for column in ("bid", "ask") if column in df.columns]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df[required].isna().any().any():
        raise ValueError("intraday bars contain NaN values")
    if not np.isfinite(df[required].to_numpy(dtype=float)).all():
        raise ValueError("intraday bars contain non-finite values")
    df = df.sort_index()
    validate_ohlcv(df[required], require_timezone=False)
    return df


def _session_timestamp(
    anchor: pd.Timestamp,
    explicit: pd.Timestamp | str | None,
    default_time: time,
) -> pd.Timestamp:
    if explicit is not None:
        ts = pd.Timestamp(explicit)
        return ts.tz_localize(anchor.tz) if ts.tzinfo is None and anchor.tz is not None else ts
    anchor_ts = pd.Timestamp(anchor)
    if anchor_ts.tzinfo is None:
        return pd.Timestamp.combine(anchor_ts.date(), default_time)
    local = anchor_ts.tz_convert(NY_TZ)
    return pd.Timestamp(datetime.combine(local.date(), default_time, tzinfo=NY_TZ)).tz_convert(
        anchor_ts.tz
    )


def _elapsed_minutes(index: pd.DatetimeIndex, session_open: pd.Timestamp) -> pd.Series:
    minutes = ((index - session_open) / pd.Timedelta(minutes=1)).astype(int)
    return pd.Series(minutes, index=index, dtype=int)


def _coerce_minute_baseline(
    baseline: Mapping[int | str, float] | pd.Series | pd.DataFrame,
) -> dict[int, float]:
    if isinstance(baseline, pd.DataFrame):
        if {"minute", "avg_volume"}.issubset(baseline.columns):
            return {
                int(row["minute"]): float(row["avg_volume"])
                for _, row in baseline[["minute", "avg_volume"]].iterrows()
            }
        if {"minute_of_session", "baseline_volume"}.issubset(baseline.columns):
            return {
                int(row["minute_of_session"]): float(row["baseline_volume"])
                for _, row in baseline[["minute_of_session", "baseline_volume"]].iterrows()
            }
        raise ValueError("minute baseline DataFrame must include minute/avg_volume columns")
    if isinstance(baseline, pd.Series):
        return {_minute_key(key): float(value) for key, value in baseline.items()}
    return {_minute_key(key): float(value) for key, value in baseline.items()}


def _minute_key(value: int | str) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if ":" in text:
        hour, minute = text.split(":", maxsplit=1)
        return (int(hour) - 9) * 60 + (int(minute) - 30)
    return int(text)


def _baseline_for_minute(baseline: dict[int, float], minute: int) -> float:
    if minute in baseline:
        return baseline[minute]
    prior = [key for key in baseline if key <= minute]
    if prior:
        return baseline[max(prior)]
    raise ValueError(f"missing minute RVOL baseline for minute {minute}")


def _opening_range(
    df: pd.DataFrame,
    session_open: pd.Timestamp,
    opening_range_minutes: int,
) -> dict[str, float]:
    cutoff = session_open + pd.Timedelta(minutes=max(1, opening_range_minutes))
    window = df[(df.index >= session_open) & (df.index < cutoff)]
    if window.empty:
        window = df.iloc[:1]
    return {"high": float(window["high"].max()), "low": float(window["low"].min())}


def _true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _spread_proxy_bps(df: pd.DataFrame) -> pd.Series:
    if {"bid", "ask"}.issubset(df.columns):
        midpoint = (df["bid"] + df["ask"]) / 2.0
        spread = (df["ask"] - df["bid"]) / midpoint * 10_000.0
        if (spread >= 0).all() and np.isfinite(spread.to_numpy(dtype=float)).all():
            return spread
    return (df["high"] - df["low"]) / df["close"] * 10_000.0


def _session_bucket(
    ts: pd.Timestamp,
    session_open: pd.Timestamp,
    session_close: pd.Timestamp,
) -> str:
    if ts < session_open:
        return "premarket"
    if ts >= session_close:
        return "after_hours"
    minutes_from_open = int((ts - session_open) / pd.Timedelta(minutes=1))
    minutes_to_close = int((session_close - ts) / pd.Timedelta(minutes=1))
    if minutes_from_open < 30:
        return "open"
    if minutes_to_close <= 60:
        return "power_hour"
    return "midday"


def _liquidity_bucket(
    dollar_volume: float,
    spread_bps: float,
    *,
    medium_dollar: float,
    high_dollar: float,
    tight_spread: float,
    wide_spread: float,
) -> str:
    if dollar_volume >= high_dollar and spread_bps <= tight_spread:
        return "high"
    if dollar_volume >= medium_dollar and spread_bps <= wide_spread:
        return "medium"
    return "low"


def _reject_non_finite(frame: pd.DataFrame, numeric_columns: Sequence[str]) -> None:
    values = frame[list(numeric_columns)].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("intraday features contain NaN or infinite values")
