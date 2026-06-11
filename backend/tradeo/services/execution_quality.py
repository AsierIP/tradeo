"""Entry-quality execution audit for real broker fills (informe §4.3 fallback).

Richer real-time microstructure feeds (bid-ask, depth, order flow) remain
unavailable — there is no provider integrated, so pre-trade microstructure
context cannot be captured yet. What *is* verifiable today is the post-trade
record the broker already gives us: fill prices, fill/submit timestamps and
commissions. This module turns that record into an auditable per-trade
entry-quality report:

- ``entry_slippage_bps`` / ``entry_slippage_r``: achieved entry fill vs the
  signal's theoretical entry, signed so positive always means "worse than
  theoretical" regardless of side.
- ``time_to_fill_s``: order submission -> entry fill latency, when both
  timestamps were recorded.
- ``commission_bps``: commission relative to the entry fill notional.
- ``estimated_vs_realized``: the pre-trade slippage/spread estimates stored on
  the trade compared with what actually happened, so estimate quality itself
  becomes auditable.

Every report carries ``data_basis`` and ``microstructure_feed`` markers making
explicit that no real-time feed backed the numbers — when a provider lands,
the method version must be bumped and the markers updated.

Shadow observations are excluded (their fills are theoretical by
construction); only trades with real broker fill provenance produce a report.
Reports are persisted idempotently on ``trade.metadata_json["execution_quality"]``
following the same pattern as ``effective_sample``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np

from tradeo.db.models import Trade
from tradeo.services.evidence import REAL_FILL_PROVENANCE

EXECUTION_QUALITY_METHOD = "fill_vs_signal_eod_v1"
DATA_BASIS = "broker_fill_record_eod_daily"
MICROSTRUCTURE_FEED = "none_available"

__all__ = [
    "EXECUTION_QUALITY_METHOD",
    "trade_execution_quality",
    "persist_execution_quality",
    "pattern_execution_quality_summary",
]


def _side_sign(side: str) -> int:
    return -1 if str(side or "").lower().strip() == "short" else 1


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def trade_execution_quality(trade: Trade) -> dict[str, Any] | None:
    """Entry-quality report for one real-fill trade, or None.

    Returns None when the trade has no real broker fill provenance or lacks
    the prices needed for an honest number (no entry fill, no theoretical
    entry). Open trades are allowed: entry quality is measurable as soon as
    the entry leg fills.
    """
    metadata = trade.metadata_json or {}
    provenance = str(metadata.get("fill_provenance") or "").strip().lower()
    if provenance not in REAL_FILL_PROVENANCE:
        return None
    theoretical_entry = _positive_float(trade.entry)
    fill_entry = _positive_float(metadata.get("entry_fill_price"))
    if theoretical_entry is None or fill_entry is None:
        return None
    sign = _side_sign(trade.side)
    shortfall = (fill_entry - theoretical_entry) * sign
    entry_slippage_bps = shortfall / theoretical_entry * 10_000.0
    risk = abs(theoretical_entry - float(trade.stop or 0.0))
    entry_slippage_r = shortfall / risk if risk > 0 else None

    submitted_at = _parse_ts(metadata.get("submitted_at"))
    fill_time = _parse_ts(
        metadata.get("entry_fill_time") or metadata.get("broker_execution_time")
    )
    time_to_fill_s: float | None = None
    if submitted_at is not None and fill_time is not None:
        delta = (fill_time - submitted_at).total_seconds()
        if delta >= 0:
            time_to_fill_s = round(delta, 3)

    commission_usd: float | None
    try:
        commission_usd = float(metadata.get("commission"))
    except (TypeError, ValueError):
        commission_usd = None
    notional = fill_entry * abs(int(trade.qty or 0))
    commission_bps = (
        round(abs(commission_usd) / notional * 10_000.0, 4)
        if commission_usd is not None and notional > 0
        else None
    )

    estimated_slippage = _positive_float(metadata.get("estimated_slippage"))
    estimated_spread_cost = _positive_float(metadata.get("estimated_spread_cost"))
    estimated_vs_realized: dict[str, Any] | None = None
    if estimated_slippage is not None or estimated_spread_cost is not None:
        estimated_total = (estimated_slippage or 0.0) + (estimated_spread_cost or 0.0)
        estimated_vs_realized = {
            "estimated_slippage_usd": estimated_slippage,
            "estimated_spread_cost_usd": estimated_spread_cost,
            "realized_entry_shortfall_per_share_usd": round(shortfall, 6),
            "estimate_error_per_share_usd": round(shortfall - estimated_total, 6),
        }

    return {
        "method": EXECUTION_QUALITY_METHOD,
        "data_basis": DATA_BASIS,
        "microstructure_feed": MICROSTRUCTURE_FEED,
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "side": str(trade.side or ""),
        "fill_provenance": provenance,
        "theoretical_entry": round(theoretical_entry, 6),
        "entry_fill_price": round(fill_entry, 6),
        "entry_slippage_bps": round(entry_slippage_bps, 4),
        "entry_slippage_r": round(entry_slippage_r, 6) if entry_slippage_r is not None else None,
        "time_to_fill_s": time_to_fill_s,
        "commission_usd": commission_usd,
        "commission_bps": commission_bps,
        "estimated_vs_realized": estimated_vs_realized,
    }


def persist_execution_quality(trades: Iterable[Trade]) -> int:
    """Store each trade's report in its metadata_json. Returns rows touched.

    Idempotent: an existing record produced by the same method from the same
    fill data is left untouched, so repeated gate evaluations do not churn
    metadata or timestamps.
    """
    now = datetime.now(timezone.utc).isoformat()
    touched = 0
    for trade in trades:
        report = trade_execution_quality(trade)
        if report is None:
            continue
        existing = (trade.metadata_json or {}).get("execution_quality")
        if existing and all(
            existing.get(key) == report[key]
            for key in (
                "method",
                "entry_fill_price",
                "entry_slippage_bps",
                "time_to_fill_s",
                "commission_bps",
            )
        ):
            continue
        record = {**report, "computed_at": now}
        trade.metadata_json = {**(trade.metadata_json or {}), "execution_quality": record}
        touched += 1
    return touched


def pattern_execution_quality_summary(trades: Iterable[Trade]) -> dict[str, Any]:
    """Distribution of entry-quality metrics across a pattern's real fills."""
    rows = [
        report
        for report in (trade_execution_quality(trade) for trade in trades)
        if report is not None
    ]
    base: dict[str, Any] = {
        "method": EXECUTION_QUALITY_METHOD,
        "data_basis": DATA_BASIS,
        "microstructure_feed": MICROSTRUCTURE_FEED,
        "count": len(rows),
        "median_entry_slippage_bps": None,
        "mean_entry_slippage_bps": None,
        "p75_entry_slippage_bps": None,
        "worst_entry_slippage_bps": None,
        "median_time_to_fill_s": None,
        "total_commission_usd": None,
        "per_trade": rows,
    }
    if not rows:
        return base
    slippage = np.asarray([row["entry_slippage_bps"] for row in rows], dtype=float)
    base["median_entry_slippage_bps"] = round(float(np.median(slippage)), 4)
    base["mean_entry_slippage_bps"] = round(float(slippage.mean()), 4)
    base["p75_entry_slippage_bps"] = round(float(np.quantile(slippage, 0.75)), 4)
    base["worst_entry_slippage_bps"] = round(float(slippage.max()), 4)
    fill_times = [row["time_to_fill_s"] for row in rows if row["time_to_fill_s"] is not None]
    if fill_times:
        base["median_time_to_fill_s"] = round(float(np.median(np.asarray(fill_times))), 3)
    commissions = [row["commission_usd"] for row in rows if row["commission_usd"] is not None]
    if commissions:
        base["total_commission_usd"] = round(float(sum(abs(c) for c in commissions)), 4)
    return base
