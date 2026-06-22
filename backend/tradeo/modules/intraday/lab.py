from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd


@dataclass(frozen=True, slots=True)
class IntradayLabObservation:
    symbol: str
    outcome_r: float
    mfe_r: float
    mae_r: float
    exit_reason: str
    bars_held: int
    eligible_evidence: bool
    shadow_only: bool = True


class IntradayLabObservationService:
    """Shadow-first triple-barrier observations; never touches broker."""

    def observe(
        self,
        bars: pd.DataFrame,
        *,
        symbol: str,
        side: str,
        entry: float,
        stop: float,
        target: float,
        opened_at: datetime,
        must_close_by: datetime,
        max_holding_bars: int,
        estimated_cost_r: float = 0.0,
    ) -> IntradayLabObservation:
        frame = bars.sort_index()
        frame = frame[(frame.index >= pd.Timestamp(_as_utc(opened_at))) & (frame.index <= pd.Timestamp(_as_utc(must_close_by)))]
        if frame.empty:
            return IntradayLabObservation(symbol.upper(), 0.0, 0.0, 0.0, "no_bars", 0, False)
        risk = abs(entry - stop)
        if risk <= 0:
            raise ValueError("entry/stop risk must be positive")
        direction = 1.0 if side.lower() == "long" else -1.0
        mfe = 0.0
        mae = 0.0
        exit_r = 0.0
        reason = "time_stop"
        held = 0
        for held, (_, row) in enumerate(frame.iloc[:max_holding_bars].iterrows(), start=1):
            high_r = (float(row["high"]) - entry) * direction / risk
            low_r = (float(row["low"]) - entry) * direction / risk
            mfe = max(mfe, high_r, low_r)
            mae = min(mae, high_r, low_r)
            if max(high_r, low_r) >= abs(target - entry) / risk:
                exit_r = abs(target - entry) / risk
                reason = "target"
                break
            if min(high_r, low_r) <= -1.0:
                exit_r = -1.0
                reason = "stop"
                break
            exit_r = (float(row["close"]) - entry) * direction / risk
        if held >= max_holding_bars and reason == "time_stop":
            reason = "max_holding_bars"
        if frame.index[min(held, len(frame)) - 1].to_pydatetime() >= _as_utc(must_close_by):
            reason = "intraday_eod_flat"
        outcome = exit_r - estimated_cost_r
        return IntradayLabObservation(
            symbol=symbol.upper(),
            outcome_r=round(outcome, 6),
            mfe_r=round(mfe, 6),
            mae_r=round(mae, 6),
            exit_reason=reason,
            bars_held=held,
            eligible_evidence=reason != "no_bars",
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
