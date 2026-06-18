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
from tradeo.services.evidence import COMMISSION_KEYS, REAL_FILL_PROVENANCE

STOP_EXIT_REASONS = {"stop_hit", "stop", "stop_gap", "stopped_out"}
TARGET_EXIT_REASONS = {"target_hit", "target", "target_gap"}

EXECUTION_ADJUSTED_R_METHOD = "realized_gross_r_minus_commission_v2"

__all__ = [
    "EXECUTION_ADJUSTED_R_METHOD",
    "trade_slippage_r",
    "trade_execution_adjusted_r",
    "pattern_slippage_summary",
    "execution_adjusted_r_summary",
]


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


def _first_float(metadata: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = metadata.get(key)
        if value is None or value == "":
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            return number
    return None


def _commission_r(trade: Trade) -> float | None:
    metadata = trade.metadata_json or {}
    commission = _first_float(metadata, COMMISSION_KEYS)
    if commission is None:
        return None
    theoretical_entry = float(trade.entry or 0.0)
    risk = abs(theoretical_entry - float(trade.stop or 0.0))
    qty = _executed_qty_for_costs(trade)
    if risk <= 0 or qty <= 0:
        return None
    return abs(commission) / (risk * qty)


def _executed_qty_for_costs(trade: Trade) -> float:
    metadata = trade.metadata_json or {}
    explicit = _first_float(metadata, ("executed_qty_for_pnl",))
    if explicit is not None and explicit > 0:
        return abs(explicit)
    entry_qty = _first_float(metadata, ("entry_fill_qty",))
    exit_qty = _first_float(metadata, ("exit_fill_qty",))
    requested = abs(float(trade.qty or 0.0))
    filled = [abs(qty) for qty in (entry_qty, exit_qty) if qty is not None and qty > 0]
    if requested > 0:
        filled.append(requested)
    return min(filled) if filled else 0.0


def trade_execution_adjusted_r(trade: Trade) -> dict[str, Any] | None:
    """Net executable R for one real-fill trade, or None when cost coverage is incomplete."""

    shortfall = trade_slippage_r(trade)
    commission_r = _commission_r(trade)
    if shortfall is None or commission_r is None:
        return None
    gross_r = float(trade.r_multiple or 0.0)
    slippage_r = float(shortfall["slippage_r"])
    commission_r_value = float(commission_r)
    expected_gross_r = gross_r + slippage_r
    net_r = gross_r - commission_r_value
    return {
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "expected_gross_r": round(float(expected_gross_r), 6),
        "gross_r": round(gross_r, 6),
        "slippage_r": round(slippage_r, 6),
        "commission_r": round(commission_r_value, 6),
        "net_r": round(float(net_r), 6),
        "gross_delta_vs_expected_r": round(float(gross_r - expected_gross_r), 6),
        "net_delta_vs_expected_r": round(float(net_r - expected_gross_r), 6),
    }


def execution_adjusted_r_summary(trades: list[Trade]) -> dict[str, Any]:
    """Net executable R with expected-vs-actual shortfall and commissions.

    ``trade.r_multiple`` is already the realized gross outcome for broker
    fills (reconciliation computes it from achieved entry/exit fills). The
    implementation shortfall explains the gap between theoretical expected R
    and actual gross R; it must not be subtracted a second time. Net executable
    R is therefore realized gross R minus explicit broker commission. Rows
    missing either component are reported as uncovered instead of silently
    treated as free execution.
    """
    rows: list[dict[str, Any]] = []
    missing_shortfall = 0
    missing_commission = 0
    for trade in trades:
        shortfall = trade_slippage_r(trade)
        commission_r = _commission_r(trade)
        if shortfall is None:
            missing_shortfall += 1
        if commission_r is None:
            missing_commission += 1
        if shortfall is None or commission_r is None:
            continue
        adjusted = trade_execution_adjusted_r(trade)
        if adjusted is not None:
            rows.append(adjusted)

    values = np.asarray([row["net_r"] for row in rows], dtype=float)
    if values.size == 0:
        return {
            "method": EXECUTION_ADJUSTED_R_METHOD,
            "count": 0,
            "coverage": 0.0,
            "missing_shortfall_rows": missing_shortfall,
            "missing_commission_rows": missing_commission,
            "expected_expectancy_r": None,
            "net_expectancy_r": None,
            "net_profit_factor": None,
            "net_max_drawdown_r": None,
            "gross_expectancy_r": None,
            "gross_delta_vs_expected_r": None,
            "net_delta_vs_expected_r": None,
            "mean_slippage_r": None,
            "mean_commission_r": None,
            "per_trade": [],
        }

    wins = [value for value in values if value > 0]
    losses = [abs(value) for value in values if value < 0]
    loss = float(sum(losses))
    expected_values = np.asarray([row["expected_gross_r"] for row in rows], dtype=float)
    gross_values = np.asarray([row["gross_r"] for row in rows], dtype=float)
    slippage_values = np.asarray([row["slippage_r"] for row in rows], dtype=float)
    commission_values = np.asarray([row["commission_r"] for row in rows], dtype=float)
    gross_delta_values = np.asarray([row["gross_delta_vs_expected_r"] for row in rows], dtype=float)
    net_delta_values = np.asarray([row["net_delta_vs_expected_r"] for row in rows], dtype=float)
    total = len(trades)
    return {
        "method": EXECUTION_ADJUSTED_R_METHOD,
        "count": int(values.size),
        "coverage": round(float(values.size / total), 4) if total else 0.0,
        "missing_shortfall_rows": missing_shortfall,
        "missing_commission_rows": missing_commission,
        "expected_expectancy_r": round(float(expected_values.mean()), 6),
        "net_expectancy_r": round(float(values.mean()), 6),
        "net_profit_factor": round(float(sum(wins) / loss), 6)
        if loss > 0
        else round(float(sum(wins)), 6)
        if wins
        else 0.0,
        "net_max_drawdown_r": round(_max_drawdown_r(values.tolist()), 6),
        "gross_expectancy_r": round(float(gross_values.mean()), 6),
        "gross_delta_vs_expected_r": round(float(gross_delta_values.mean()), 6),
        "net_delta_vs_expected_r": round(float(net_delta_values.mean()), 6),
        "mean_slippage_r": round(float(slippage_values.mean()), 6),
        "mean_commission_r": round(float(commission_values.mean()), 6),
        "per_trade": rows,
    }


def _max_drawdown_r(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return max_drawdown
