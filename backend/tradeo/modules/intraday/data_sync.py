from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class IntradayDataManifest:
    symbol: str
    timeframe: str
    session_id: str
    complete_bars: int
    first_bar_at: datetime | None
    last_bar_at: datetime | None
    last_eligible_bar_at: datetime | None
    stale: bool
    gap_count: int
    duplicate_count: int
    zero_volume_count: int
    roles: dict[str, int]


@dataclass(frozen=True, slots=True)
class IntradayDataSyncResult:
    bars: pd.DataFrame
    manifest: IntradayDataManifest
    reason_codes: tuple[str, ...]


class IntradayDataSync:
    """Validate and serve closed intraday bars only."""

    def sync(
        self,
        bars: pd.DataFrame,
        *,
        symbol: str,
        timeframe: str,
        session_id: str,
        now: datetime,
        stale_after_seconds: int = 900,
    ) -> IntradayDataSyncResult:
        frame, duplicate_count = _normalize(bars)
        closed = _closed_bars(frame, timeframe=timeframe, now=now)
        reason_codes: list[str] = []
        if closed.empty:
            reason_codes.append("no_complete_bars")
        gap_count = _gap_count(closed, timeframe)
        if gap_count:
            reason_codes.append("unexpected_gaps")
        zero_volume_count = int((closed["volume"] <= 0).sum()) if not closed.empty else 0
        if zero_volume_count:
            reason_codes.append("zero_volume")
        if duplicate_count:
            reason_codes.append("duplicates_removed")
        last_at = closed.index[-1].to_pydatetime() if not closed.empty else None
        stale = bool(last_at and (_as_utc(now) - _as_utc(last_at)).total_seconds() > stale_after_seconds)
        if stale:
            reason_codes.append("stale")
        manifest = IntradayDataManifest(
            symbol=symbol.upper(),
            timeframe=timeframe,
            session_id=session_id,
            complete_bars=len(closed),
            first_bar_at=closed.index[0].to_pydatetime() if not closed.empty else None,
            last_bar_at=last_at,
            last_eligible_bar_at=last_at if not stale else None,
            stale=stale,
            gap_count=gap_count,
            duplicate_count=duplicate_count,
            zero_volume_count=zero_volume_count,
            roles=_roles(len(closed)),
        )
        return IntradayDataSyncResult(closed, manifest, tuple(reason_codes))


def _normalize(bars: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("intraday bars require DatetimeIndex")
    frame = bars.copy()
    frame.columns = [str(col).lower() for col in frame.columns]
    required = ["open", "high", "low", "close", "volume"]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    frame = frame[required].sort_index()
    duplicate_count = int(frame.index.duplicated(keep="last").sum())
    frame = frame[~frame.index.duplicated(keep="last")]
    for col in required:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if frame[required].isna().any().any() or not np.isfinite(frame[required].to_numpy(dtype=float)).all():
        raise ValueError("intraday bars contain NaN or infinite values")
    return frame, duplicate_count


def _closed_bars(frame: pd.DataFrame, *, timeframe: str, now: datetime) -> pd.DataFrame:
    delta = _timeframe_delta(timeframe)
    current = pd.Timestamp(_as_utc(now))
    cutoff = current - delta
    return frame[frame.index <= cutoff]


def _gap_count(frame: pd.DataFrame, timeframe: str) -> int:
    if len(frame) < 2:
        return 0
    expected = pd.Timedelta(_timeframe_delta(timeframe))
    diffs = frame.index.to_series().diff().dropna()
    return int((diffs > expected * 1.5).sum())


def _roles(count: int) -> dict[str, int]:
    return {
        "context": count,
        "setup": min(count, 80),
        "trigger": min(count, 20),
        "execution_monitor": min(count, 5),
    }


def _timeframe_delta(timeframe: str):
    value = timeframe.strip().lower()
    if value.endswith("m"):
        return pd.Timedelta(minutes=int(value[:-1])).to_pytimedelta()
    if value.endswith("h"):
        return pd.Timedelta(hours=int(value[:-1])).to_pytimedelta()
    return pd.Timedelta(minutes=5).to_pytimedelta()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
