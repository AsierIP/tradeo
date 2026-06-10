"""Implementation shortfall / slippage_R per trade and per pattern (informe §4.6).

For every closed trade with a real broker fill we compare the achieved fills
against the theoretical prices the Research labeler assumes:

    shortfall_entry = (fill_entry - theoretical_entry) * side_sign
    shortfall_exit  = (theoretical_exit - fill_exit) * side_sign
    slippage_R      = (shortfall_entry + shortfall_exit) / risk_per_share

Theoretical entry is the signal entry price; theoretical exit depends on the
exit reason (stop -> stop price, target -> target price, time stop -> the
achieved close, which contributes zero by construction). Shadow observations
are excluded: their fills are theoretical, so their shortfall is zero by
definition and would dilute the distribution the Director gate looks at.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from tradeo.db.models import Trade
from tradeo.services.evidence import REAL_FILL_PROVENANCE

STOP_EXIT_REASONS = {"stop_hit", "stop", "stop_gap", "stopped_out"}
TARGET_EXIT_REASONS = {"target_hit", "target", "target_gap"}

__all__ = ["trade_slippage_r", "pattern_slippage_summary"]


def _side_sign(side: str) -> int:
    return -1 if str(side or "").lower().strip() == "short" else 1


def _has_real_fill(trade: Trade) -> bool:
    metadata = trade.metadata_json or {}
    provenance = str(metadata.get("fill_provenance") or "").strip().lower()
    return provenance in REAL_FILL_PROVENANCE


def trade_slippage_r(trade: Trade) -> dict[str, Any] | None:
    """Slippage in R for one closed trade with real fills, or None.

    Returns None when the trade has no real broker fill provenance, is not
    closed, or lacks the data needed for an honest number (no fill prices,
    zero risk per share).
    """
    if trade.closed_at is None and str(getattr(trade.status, "value", trade.status)) != "closed":
        return None
    if not _has_real_fill(trade):
        return None
    metadata = trade.metadata_json or {}
    theoretical_entry = float(trade.entry or 0.0)
    risk = abs(theoretical_entry - float(trade.stop or 0.0))
    if risk <= 0 or theoretical_entry <= 0:
        return None
    try:
        fill_entry = float(metadata.get("entry_fill_price") or 0.0)
    except (TypeError, ValueError):
        return None
    if fill_entry <= 0:
        return None
    fill_exit_raw = metadata.get("exit_fill_price", trade.exit_price)
    try:
        fill_exit = float(fill_exit_raw or 0.0)
    except (TypeError, ValueError):
        return None
    if fill_exit <= 0:
        return None
    exit_reason = str(metadata.get("exit_reason") or "").strip().lower()
    if exit_reason in STOP_EXIT_REASONS:
        theoretical_exit = float(trade.stop)
    elif exit_reason in TARGET_EXIT_REASONS:
        theoretical_exit = float(trade.target)
    else:
        # Time stop or unknown: the labeler assumes exit at the achieved
        # close, so the exit leg contributes no measurable shortfall.
        theoretical_exit = fill_exit
    sign = _side_sign(trade.side)
    shortfall_entry = (fill_entry - theoretical_entry) * sign
    shortfall_exit = (theoretical_exit - fill_exit) * sign
    slippage = (shortfall_entry + shortfall_exit) / risk
    return {
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "exit_reason": exit_reason or "unknown",
        "shortfall_entry_r": round(shortfall_entry / risk, 6),
        "shortfall_exit_r": round(shortfall_exit / risk, 6),
        "slippage_r": round(float(slippage), 6),
    }


def pattern_slippage_summary(trades: list[Trade]) -> dict[str, Any]:
    """Distribution of slippage_R across a pattern's real-fill trades."""
    rows = [row for row in (trade_slippage_r(trade) for trade in trades) if row is not None]
    values = np.asarray([row["slippage_r"] for row in rows], dtype=float)
    if values.size == 0:
        return {
            "count": 0,
            "median_slippage_r": None,
            "mean_slippage_r": None,
            "p75_slippage_r": None,
            "worst_slippage_r": None,
            "per_trade": [],
        }
    return {
        "count": int(values.size),
        "median_slippage_r": round(float(np.median(values)), 6),
        "mean_slippage_r": round(float(values.mean()), 6),
        "p75_slippage_r": round(float(np.quantile(values, 0.75)), 6),
        "worst_slippage_r": round(float(values.max()), 6),
        "per_trade": rows,
    }
