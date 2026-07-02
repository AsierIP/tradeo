from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Literal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

VWAPPriceMode = Literal["typical", "close"]


@dataclass(frozen=True, slots=True)
class IntradayVWAPFeatureResult:
    frame: pd.DataFrame
    metadata: dict[str, object]


def build_intraday_vwap_features(
    bars: pd.DataFrame,
    *,
    price_mode: VWAPPriceMode = "typical",
    session_tz: str = "America/New_York",
    session_start: str = "09:30",
    session_end: str = "16:00",
    timestamp_column: str | None = None,
    atr_column: str | None = None,
    slope_lookback: int = 3,
    flat_slope_bps: float = 1.0,
    extension_bps: float = 100.0,
) -> IntradayVWAPFeatureResult:
    """Build causal intraday VWAP features.

    All rolling state resets by regular US session. The function only uses the
    current and previous closed bars; no forward labels are produced here.
    """

    if slope_lookback < 1:
        raise ValueError("slope_lookback must be >= 1")
    if flat_slope_bps < 0:
        raise ValueError("flat_slope_bps must be >= 0")
    if extension_bps <= 0:
        raise ValueError("extension_bps must be > 0")

    frame = _prepare_frame(bars, timestamp_column=timestamp_column)
    metadata: dict[str, object] = {
        "price_mode": price_mode,
        "session_tz": session_tz,
        "session_start": session_start,
        "session_end": session_end,
        "no_lookahead": True,
        "session_inference": "regular_us_session",
    }
    if frame.empty:
        metadata["empty_input"] = True
        return IntradayVWAPFeatureResult(frame=_with_empty_columns(frame), metadata=metadata)

    _require_columns(frame, {"high", "low", "close", "volume"})
    local_index, timezone_note = _localize_index(frame.index, session_tz=session_tz)
    metadata["timezone_assumption"] = timezone_note

    result = frame.copy()
    result.index = local_index
    result["session_date"] = pd.Series(local_index.date, index=result.index).astype(str)
    start = _parse_session_time(session_start)
    end = _parse_session_time(session_end)
    local_times = pd.Series(local_index.time, index=result.index)
    in_session = (local_times >= start) & (local_times < end)
    result["in_regular_session"] = in_session.to_numpy(dtype=bool)
    result["session_bucket"] = _session_buckets(local_index, in_session, start=start, end=end)

    source_price = _source_price(result, price_mode)
    volume = pd.to_numeric(result["volume"], errors="coerce").fillna(0.0).clip(lower=0.0)
    weighted_price = source_price * volume
    session_key = result["session_date"].where(result["in_regular_session"], "__out_of_session__")
    session_cum_volume = volume.where(result["in_regular_session"], 0.0).groupby(session_key).cumsum()
    session_cum_value = weighted_price.where(result["in_regular_session"], 0.0).groupby(session_key).cumsum()
    result["vwap"] = (session_cum_value / session_cum_volume.replace(0.0, np.nan)).where(
        result["in_regular_session"]
    )

    close = pd.to_numeric(result["close"], errors="coerce")
    distance_fraction = close / result["vwap"] - 1.0
    result["vwap_distance_pct"] = distance_fraction * 100.0
    result["vwap_distance_bps"] = distance_fraction * 10_000.0
    if atr_column and atr_column in result.columns:
        atr = pd.to_numeric(result[atr_column], errors="coerce").replace(0.0, np.nan)
        result["vwap_distance_atr"] = (close - result["vwap"]) / atr
    else:
        result["vwap_distance_atr"] = "not_available"

    result["above_vwap"] = (close > result["vwap"]).fillna(False)
    result["below_vwap"] = (close < result["vwap"]).fillna(False)
    prev_close = close.groupby(session_key).shift(1)
    prev_vwap = result["vwap"].groupby(session_key).shift(1)
    result["crossed_above_vwap"] = ((close > result["vwap"]) & (prev_close <= prev_vwap)).fillna(False)
    result["crossed_below_vwap"] = ((close < result["vwap"]) & (prev_close >= prev_vwap)).fillna(False)
    result["bars_since_vwap_cross"] = _bars_since_cross(
        result["crossed_above_vwap"] | result["crossed_below_vwap"],
        result["in_regular_session"],
        session_key,
    )

    previous_vwap = result["vwap"].groupby(session_key).shift(slope_lookback)
    result["vwap_slope_bps"] = (result["vwap"] / previous_vwap - 1.0) * 10_000.0
    result["vwap_slope_direction"] = _slope_direction(result["vwap_slope_bps"], flat_slope_bps)

    previous_above = result["above_vwap"].groupby(session_key).shift(1).fillna(False)
    previous_below = result["below_vwap"].groupby(session_key).shift(1).fillna(False)
    high = pd.to_numeric(result["high"], errors="coerce")
    low = pd.to_numeric(result["low"], errors="coerce")

    result["vwap_reclaim_long"] = result["crossed_above_vwap"] & result["vwap_slope_direction"].isin(["up", "flat"])
    result["vwap_loss_long_exit"] = result["crossed_below_vwap"]
    result["vwap_hold_long"] = result["above_vwap"] & previous_above & (low <= result["vwap"])
    result["vwap_reject_short"] = result["below_vwap"] & (high >= result["vwap"]) & previous_below
    result["vwap_loss_short"] = result["crossed_below_vwap"] & result["vwap_slope_direction"].isin(["down", "flat"])
    result["vwap_reclaim_short_exit"] = result["crossed_above_vwap"]
    result["vwap_extension_up"] = result["vwap_distance_bps"] >= float(extension_bps)
    result["vwap_extension_down"] = result["vwap_distance_bps"] <= -float(extension_bps)
    result["vwap_mean_reversion_candidate"] = (
        result["vwap_extension_up"] | result["vwap_extension_down"]
    ) & result["vwap_slope_direction"].isin(["up", "down", "flat"])

    return IntradayVWAPFeatureResult(frame=result, metadata=metadata)


def _prepare_frame(bars: pd.DataFrame, *, timestamp_column: str | None) -> pd.DataFrame:
    if timestamp_column:
        if timestamp_column not in bars.columns:
            raise ValueError(f"timestamp_column {timestamp_column!r} is missing")
        frame = bars.copy()
        frame.index = pd.to_datetime(frame.pop(timestamp_column))
        return frame.sort_index()
    return bars.copy().sort_index()


def _require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"missing required OHLCV columns: {', '.join(missing)}")


def _source_price(frame: pd.DataFrame, price_mode: VWAPPriceMode) -> pd.Series:
    if price_mode == "typical":
        return (
            pd.to_numeric(frame["high"], errors="coerce")
            + pd.to_numeric(frame["low"], errors="coerce")
            + pd.to_numeric(frame["close"], errors="coerce")
        ) / 3.0
    if price_mode == "close":
        return pd.to_numeric(frame["close"], errors="coerce")
    raise ValueError(f"unsupported price_mode: {price_mode}")


def _localize_index(index: pd.Index, *, session_tz: str) -> tuple[pd.DatetimeIndex, str]:
    dt_index = pd.DatetimeIndex(pd.to_datetime(index))
    tz = ZoneInfo(session_tz)
    if dt_index.tz is None:
        return dt_index.tz_localize(tz), f"naive_index_localized_to_{session_tz}"
    return dt_index.tz_convert(tz), "timezone_aware_converted_to_session_tz"


def _parse_session_time(raw: str) -> time:
    hour, minute = raw.split(":", maxsplit=1)
    return time(int(hour), int(minute))


def _session_buckets(
    index: pd.DatetimeIndex,
    in_session: pd.Series,
    *,
    start: time,
    end: time,
) -> pd.Series:
    buckets: list[str] = []
    for ts, is_regular in zip(index, in_session, strict=True):
        if not is_regular:
            buckets.append("out_of_session")
            continue
        minutes = ts.hour * 60 + ts.minute
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        if minutes < start_minutes + 60:
            buckets.append("open")
        elif minutes >= end_minutes - 60:
            buckets.append("close")
        else:
            buckets.append("mid")
    return pd.Series(buckets, index=index)


def _bars_since_cross(crossed: pd.Series, in_session: pd.Series, session_key: pd.Series) -> pd.Series:
    values = pd.Series(pd.NA, index=crossed.index, dtype="Int64")
    for _, positions in crossed.groupby(session_key).groups.items():
        count: int | None = None
        for pos in positions:
            if not bool(in_session.loc[pos]):
                values.loc[pos] = pd.NA
                continue
            if bool(crossed.loc[pos]):
                count = 0
            elif count is not None:
                count += 1
            values.loc[pos] = count if count is not None else pd.NA
    return values


def _slope_direction(slope_bps: pd.Series, flat_slope_bps: float) -> pd.Series:
    direction = pd.Series("unknown", index=slope_bps.index, dtype="object")
    direction = direction.mask(slope_bps > flat_slope_bps, "up")
    direction = direction.mask(slope_bps < -flat_slope_bps, "down")
    direction = direction.mask(slope_bps.abs() <= flat_slope_bps, "flat")
    return direction


def _with_empty_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    columns = [
        "session_date",
        "in_regular_session",
        "session_bucket",
        "vwap",
        "vwap_distance_pct",
        "vwap_distance_bps",
        "vwap_distance_atr",
        "above_vwap",
        "below_vwap",
        "crossed_above_vwap",
        "crossed_below_vwap",
        "bars_since_vwap_cross",
        "vwap_slope_bps",
        "vwap_slope_direction",
        "vwap_reclaim_long",
        "vwap_loss_long_exit",
        "vwap_hold_long",
        "vwap_reject_short",
        "vwap_loss_short",
        "vwap_reclaim_short_exit",
        "vwap_extension_up",
        "vwap_extension_down",
        "vwap_mean_reversion_candidate",
    ]
    for column in columns:
        result[column] = pd.Series(dtype="object")
    return result
