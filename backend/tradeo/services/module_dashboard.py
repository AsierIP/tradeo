from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy.orm import Session, joinedload

from tradeo.db.models import Signal, Trade
from tradeo.services.evidence import (
    EvidenceQuality,
    SHADOW_EVIDENCE_TYPES,
    evidence_metadata_with_stored_columns,
    evidence_quality_from_metadata,
    evidence_type_from_metadata,
    is_strong_fill_evidence,
)

EntryModule = Literal["laboratory", "fox_hunter"]

MODULE_DASHBOARD_QUERY_LIMIT = 500
PNL_BASIS = "operational_fills_only"


def module_overview(db: Session, module: EntryModule, *, limit: int = 80) -> dict[str, Any]:
    signals = [
        signal
        for signal in db.query(Signal).order_by(Signal.created_at.desc()).limit(MODULE_DASHBOARD_QUERY_LIMIT).all()
        if _signal_module(signal) == module
    ][:limit]
    signal_ids = {signal.id for signal in signals}
    all_trades = [
        trade
        for trade in (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .order_by(Trade.opened_at.desc())
            .limit(MODULE_DASHBOARD_QUERY_LIMIT)
            .all()
        )
        if _trade_module(trade) == module or (trade.signal_id in signal_ids)
    ][:limit]
    signal_trade_statuses = _signal_trade_statuses(all_trades)
    trades = [trade for trade in all_trades if _status_value(trade.status) != "cancelled"]
    execution_trades = [trade for trade in trades if _is_normal_fill_evidence(trade)]
    pnl_points = _pnl_points(list(reversed(execution_trades)))
    total_pnl = pnl_points[-1]["total_pnl_usd"] if pnl_points else 0.0
    all_closed_trades = [trade for trade in trades if _status_value(trade.status) == "closed"]
    execution_closed_trades = [
        trade for trade in all_closed_trades if _is_normal_fill_evidence(trade)
    ]
    signal_payloads = [_signal_to_dict(signal, signal_trade_statuses.get(signal.id)) for signal in signals]
    trade_payloads = [_trade_to_dict(trade) for trade in trades]
    evidence_summary = _evidence_summary(trades)
    return {
        "module": module,
        "data_scope": f"last_{MODULE_DASHBOARD_QUERY_LIMIT}_query/limit_{limit}",
        "query_limit": MODULE_DASHBOARD_QUERY_LIMIT,
        "summary_limit": limit,
        "pnl_basis": PNL_BASIS,
        "director_source": False,
        "scope_note": (
            "Operational dashboard summary only; Director review must use audit/export sources."
        ),
        "signals": signal_payloads,
        "trades": trade_payloads,
        "pattern_outcomes": _pattern_outcomes(signal_payloads, trade_payloads),
        "pnl_points": pnl_points,
        "shadow_pnl_points": _pnl_points(
            list(reversed([trade for trade in trades if _is_shadow_evidence(trade)]))
        ),
        "evidence_summary": evidence_summary,
        "stats": {
            "signals": len(signals),
            "trades": len(trades),
            "open_trades": sum(1 for trade in trades if _status_value(trade.status) == "open"),
            "closed_trades": len(execution_closed_trades),
            "all_closed_trades": len(all_closed_trades),
            "execution_closed_trades": len(execution_closed_trades),
            "shadow_closed_trades": evidence_summary["shadow_closed"],
            "near_miss_closed_trades": evidence_summary["near_miss_closed"],
            "ibkr_paper_filled_trades": evidence_summary["ibkr_paper_filled"],
            "live_trades": evidence_summary["live_filled"],
            "live_filled_trades": evidence_summary["live_filled"],
            "degraded_closed_trades": evidence_summary["degraded_closed"],
            "total_pnl_usd": total_pnl,
            "total_r": round(sum(float(trade.r_multiple or 0.0) for trade in execution_closed_trades), 4),
            "shadow_total_r": round(
                sum(float(trade.r_multiple or 0.0) for trade in all_closed_trades if _is_shadow_evidence(trade)),
                4,
            ),
            "pnl_basis": PNL_BASIS,
            "shadow_only": len(execution_closed_trades) == 0
            and (evidence_summary["shadow_closed"] > 0 or evidence_summary["near_miss_closed"] > 0),
            "win_rate": (
                sum(1 for trade in execution_closed_trades if float(trade.pnl_usd or 0.0) > 0)
                / len(execution_closed_trades)
                if execution_closed_trades
                else 0.0
            ),
            "funnel": _signal_funnel(signal_payloads),
        },
    }


def _signal_module(signal: Signal) -> str:
    metadata = signal.metadata_json or {}
    entry_module = metadata.get("entry_module")
    if entry_module:
        return str(entry_module)
    if signal.strategy_version.startswith("fox_hunter_"):
        return "fox_hunter"
    purpose = str(metadata.get("purpose") or "")
    if signal.strategy_version.startswith(("laboratory_", "ibkr_paper_", "ibkr_smoke_")) or purpose.startswith("ibkr_paper_"):
        return "laboratory"
    return "defined"


def _trade_module(trade: Trade) -> str:
    if trade.signal is not None:
        return _signal_module(trade.signal)
    metadata = trade.metadata_json or {}
    source_module = metadata.get("entry_module") or metadata.get("source_module")
    if source_module:
        return str(source_module)
    reason = str(metadata.get("reason") or "")
    if reason.startswith("fox_hunter"):
        return "fox_hunter"
    if reason.startswith("laboratory"):
        return "laboratory"
    execution_mode = str(metadata.get("execution_mode") or "")
    if execution_mode == "paper":
        return "laboratory"
    if metadata.get("ibkr_mode") == "paper":
        return "laboratory"
    return "defined"


def _pnl_points(trades: list[Trade]) -> list[dict[str, Any]]:
    total = 0.0
    points = [{"timestamp": datetime.now().isoformat(), "total_pnl_usd": 0.0, "trade_pnl_usd": 0.0}]
    for trade in trades:
        pnl = float(trade.pnl_usd or 0.0)
        total += pnl
        timestamp = trade.closed_at or trade.opened_at
        points.append(
            {
                "timestamp": timestamp.isoformat() if timestamp else "",
                "total_pnl_usd": round(total, 2),
                "trade_pnl_usd": round(pnl, 2),
                "symbol": trade.symbol,
                "status": _status_value(trade.status),
            }
        )
    return points


def _status_value(status: Any) -> str:
    return str(status.value if hasattr(status, "value") else status)


def _signal_trade_statuses(trades: list[Trade]) -> dict[int, dict[str, Any]]:
    status_by_signal: dict[int, dict[str, Any]] = {}
    for trade in trades:
        if trade.signal_id is None:
            continue
        trade_status = _status_value(trade.status)
        current = status_by_signal.get(trade.signal_id)
        evidence_type = _trade_evidence_type(trade)
        if evidence_type in SHADOW_EVIDENCE_TYPES:
            is_closed = trade_status == "closed"
            status_by_signal[trade.signal_id] = {
                "status": _execution_class_from_evidence(evidence_type, trade_status),
                "reason_code": evidence_type,
                "reason": (
                    "Lab shadow observation closed without broker order"
                    if is_closed
                    else "Lab shadow observation is open without broker order"
                ),
                "retryable": False,
                "next_action": "review_shadow_outcome" if is_closed else "collect_shadow_outcome",
            }
            continue
        if trade_status in {"open", "closed"}:
            metadata = trade.metadata_json or {}
            execution_mode = str(metadata.get("execution_mode") or "")
            if trade_status == "open" and execution_mode == "ibkr":
                status_by_signal[trade.signal_id] = {
                    "status": "order_submitted",
                    "reason_code": "ibkr_order_submitted_waiting_fill",
                    "reason": "IBKR bracket was accepted; fill status still needs broker reconciliation",
                    "retryable": False,
                    "next_action": "monitor_order_fill",
                }
                continue
            status_by_signal[trade.signal_id] = {
                "status": "executed",
                "reason_code": f"trade_{trade_status}",
                "reason": f"Trade is {trade_status}",
                "retryable": False,
                "next_action": "monitor_trade" if trade_status == "open" else "review_closed_trade",
            }
        elif current is None:
            outcome = (trade.metadata_json or {}).get("execution_outcome") or {}
            status_by_signal[trade.signal_id] = {
                "status": outcome.get("status", "order_cancelled"),
                "reason_code": outcome.get("reason_code", "order_cancelled"),
                "reason": outcome.get("reason", "Order was cancelled before becoming an active trade"),
                "retryable": bool(outcome.get("retryable", True)),
                "next_action": outcome.get("next_action", "retry_order_submission"),
            }
    return status_by_signal


def _signal_execution_outcome(signal: Signal, trade_status: dict[str, Any] | None = None) -> dict[str, Any]:
    if trade_status:
        return trade_status
    metadata = signal.metadata_json or {}
    if isinstance(metadata.get("execution_outcome"), dict):
        return metadata["execution_outcome"]
    signal_status = _status_value(signal.status)
    if signal_status == "expired":
        return {
            "status": "entry_expired",
            "reason_code": "entry_price_missed_or_signal_expired",
            "reason": "Entry signal expired before execution",
            "retryable": False,
            "next_action": "discard_signal",
        }
    if signal.human_approved or signal_status == "executed":
        return {
            "status": "retry_order_submission",
            "reason_code": "no_trade_recorded",
            "reason": "Signal was approved for execution but no active or closed trade exists",
            "retryable": True,
            "next_action": "retry_order_submission",
        }
    return {
        "status": signal_status,
        "reason_code": "not_submitted",
        "reason": "Signal is stored but order execution was not requested",
        "retryable": False,
        "next_action": "wait_for_execution_approval",
    }


def _signal_to_dict(signal: Signal, trade_status: dict[str, Any] | None = None) -> dict[str, Any]:
    outcome = _signal_execution_outcome(signal, trade_status)
    display_status = str(outcome.get("status") or _status_value(signal.status))
    metadata = signal.metadata_json or {}
    entry_quality = metadata.get("entry_quality") if isinstance(metadata.get("entry_quality"), dict) else {}
    signal_snapshot = (
        metadata.get("signal_snapshot") if isinstance(metadata.get("signal_snapshot"), dict) else {}
    )
    quality_score = _entry_quality_score(signal, entry_quality)
    return {
        "id": signal.id,
        "symbol": signal.symbol,
        "pattern": signal.pattern,
        "side": signal.side,
        "timeframe": signal.timeframe,
        "entry": signal.entry,
        "stop": signal.stop,
        "target": signal.target,
        "reward_risk": signal.reward_risk,
        "confidence": signal.confidence,
        "composite_score": signal.composite_score,
        "entry_quality_score": quality_score,
        "entry_quality_label": entry_quality.get("label") or _entry_quality_label(quality_score),
        "entry_quality_actionable": bool(entry_quality.get("actionable", quality_score >= 0.60)),
        "entry_quality_flags": list(entry_quality.get("flags") or []),
        "opportunity_rank": metadata.get("opportunity_rank"),
        "opportunity_rank_score": metadata.get("opportunity_rank_score"),
        "risk_usd": signal.risk_usd,
        "suggested_qty": signal.suggested_qty,
        "strategy_version": signal.strategy_version,
        "status": display_status,
        "execution_reason_code": outcome.get("reason_code"),
        "execution_reason": outcome.get("reason"),
        "retryable": bool(outcome.get("retryable", False)),
        "next_action": outcome.get("next_action"),
        "supervisor_notes": signal.supervisor_notes,
        "human_approved": signal.human_approved,
        "created_at": signal.created_at.isoformat() if signal.created_at else "",
        "signal_snapshot": signal_snapshot,
        "metadata_json": metadata,
    }


def _trade_to_dict(trade: Trade) -> dict[str, Any]:
    metadata = _trade_evidence_metadata(trade)
    evidence_type = _trade_evidence_type(trade)
    evidence_quality = evidence_quality_from_metadata(metadata)
    return {
        "id": trade.id,
        "signal_id": trade.signal_id,
        "symbol": trade.symbol,
        "pattern": trade.pattern,
        "side": trade.side,
        "qty": trade.qty,
        "entry": trade.entry,
        "stop": trade.stop,
        "target": trade.target,
        "status": _status_value(trade.status),
        "opened_at": trade.opened_at.isoformat() if trade.opened_at else "",
        "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
        "exit_price": trade.exit_price,
        "pnl_usd": trade.pnl_usd,
        "r_multiple": trade.r_multiple,
        "broker_order_id": trade.broker_order_id,
        "evidence_type": evidence_type,
        "execution_class": _execution_class_from_evidence(evidence_type, _status_value(trade.status)),
        "evidence_quality": evidence_quality,
        "counts_as_execution_fill": _is_normal_fill_evidence(trade),
        "metadata_json": trade.metadata_json or {},
    }


def _trade_evidence_type(trade: Trade) -> str:
    return evidence_type_from_metadata(
        _trade_evidence_metadata(trade),
        status=_status_value(trade.status),
        signal_metadata=(trade.signal.metadata_json if trade.signal is not None else {}) or {},
        broker_order_id=trade.broker_order_id,
    )


def _execution_class_from_evidence(evidence_type: str | None, status: str) -> str:
    if evidence_type == "near_miss_shadow":
        return "near_miss_closed" if status == "closed" else "near_miss_open"
    if evidence_type == "shadow_no_order":
        return "shadow_closed" if status == "closed" else "shadow_open"
    if evidence_type == "ibkr_paper_fill":
        return "ibkr_paper_filled"
    if evidence_type == "ibkr_paper_order":
        return "ibkr_paper_order"
    if evidence_type in {"live_fill", "live_order"}:
        return "live"
    return "unknown"


def _is_normal_fill_evidence(trade: Trade) -> bool:
    return is_strong_fill_evidence(
        _trade_evidence_metadata(trade),
        trade_status=_status_value(trade.status),
        signal_metadata=(trade.signal.metadata_json if trade.signal is not None else {}) or {},
        broker_order_id=trade.broker_order_id,
    )


def _is_shadow_evidence(trade: Trade) -> bool:
    return _trade_evidence_type(trade) in SHADOW_EVIDENCE_TYPES


def _evidence_summary(trades: list[Trade]) -> dict[str, int]:
    summary = {
        "shadow_closed": 0,
        "near_miss_closed": 0,
        "ibkr_paper_filled": 0,
        "live_filled": 0,
        "degraded_closed": 0,
    }
    for trade in trades:
        if _status_value(trade.status) != "closed":
            continue
        evidence_type = _trade_evidence_type(trade)
        metadata = _trade_evidence_metadata(trade)
        evidence_quality = evidence_quality_from_metadata(metadata)
        if evidence_type == "near_miss_shadow":
            summary["near_miss_closed"] += 1
        elif evidence_type == "shadow_no_order":
            summary["shadow_closed"] += 1
        elif evidence_type == "ibkr_paper_fill" and _is_normal_fill_evidence(trade):
            summary["ibkr_paper_filled"] += 1
        elif evidence_type == "live_fill" and _is_normal_fill_evidence(trade):
            summary["live_filled"] += 1
        if evidence_quality == EvidenceQuality.DEGRADED.value:
            summary["degraded_closed"] += 1
    return summary


def _trade_evidence_metadata(trade: Trade) -> dict[str, Any]:
    return evidence_metadata_with_stored_columns(
        trade.metadata_json or {},
        evidence_type=trade.evidence_type,
        evidence_quality=trade.evidence_quality,
    )


def _entry_quality_score(signal: Signal, entry_quality: dict[str, Any]) -> float:
    metadata = signal.metadata_json or {}
    value = entry_quality.get("score", metadata.get("entry_quality_score", signal.composite_score))
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return round(float(signal.composite_score or 0.0), 6)


def _entry_quality_label(score: float) -> str:
    if score >= 0.78:
        return "high"
    if score >= 0.60:
        return "actionable"
    if score >= 0.45:
        return "watch"
    return "weak"


def _signal_funnel(signals: list[dict[str, Any]]) -> dict[str, int]:
    submitted_statuses = {
        "retry_order_submission",
        "order_submitted",
        "executed",
        "order_cancelled",
    }
    executed_statuses = {"order_submitted", "executed"}
    blocked_statuses = {"entry_expired", "order_cancelled", "rejected"}
    return {
        "detected": len(signals),
        "actionable": sum(1 for signal in signals if bool(signal.get("entry_quality_actionable"))),
        "submitted": sum(
            1
            for signal in signals
            if bool(signal.get("human_approved")) or str(signal.get("status")) in submitted_statuses
        ),
        "executed": sum(1 for signal in signals if str(signal.get("status")) in executed_statuses),
        "blocked_or_expired": sum(
            1
            for signal in signals
            if str(signal.get("status")) in blocked_statuses or bool(signal.get("entry_quality_flags"))
        ),
    }


def _pattern_outcomes(
    signals: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    submitted_statuses = {
        "retry_order_submission",
        "order_submitted",
        "executed",
        "order_cancelled",
    }
    executed_statuses = {"order_submitted", "executed"}
    blocked_statuses = {"entry_expired", "order_cancelled", "rejected"}
    for signal in signals:
        pattern = str(signal.get("pattern") or "unknown")
        row = _pattern_row(rows, pattern)
        row["signals"] += 1
        row["actionable"] += 1 if bool(signal.get("entry_quality_actionable")) else 0
        row["submitted"] += 1 if bool(signal.get("human_approved")) or str(signal.get("status")) in submitted_statuses else 0
        row["executed"] += 1 if str(signal.get("status")) in executed_statuses else 0
        row["blocked_or_expired"] += (
            1
            if str(signal.get("status")) in blocked_statuses or bool(signal.get("entry_quality_flags"))
            else 0
        )
        quality = float(signal.get("entry_quality_score") or 0.0)
        row["_quality_sum"] += quality
        reason_code = str(signal.get("execution_reason_code") or "unknown")
        row["reason_counts"][reason_code] = row["reason_counts"].get(reason_code, 0) + 1
    for trade in trades:
        pattern = str(trade.get("pattern") or "unknown")
        row = _pattern_row(rows, pattern)
        evidence_type = str(trade.get("evidence_type") or "")
        evidence_quality = str(trade.get("evidence_quality") or "")
        counts_as_execution = bool(trade.get("counts_as_execution_fill"))
        row["trades"] += 1
        if str(trade.get("status")) == "open":
            row["open_trades"] += 1
        if str(trade.get("status")) == "closed":
            row["all_closed_trades"] += 1
            if evidence_type == "near_miss_shadow":
                row["near_miss_closed"] += 1
            elif evidence_type == "shadow_no_order":
                row["shadow_closed"] += 1
            elif evidence_type == "ibkr_paper_fill" and counts_as_execution:
                row["ibkr_paper_filled"] += 1
            elif evidence_type == "live_fill" and counts_as_execution:
                row["live_filled"] += 1
                row["live"] += 1
            if evidence_quality == "degraded":
                row["degraded_closed"] += 1
        if counts_as_execution:
            row["closed_trades"] += 1
            row["total_pnl_usd"] += float(trade.get("pnl_usd") or 0.0)
            row["total_r"] += float(trade.get("r_multiple") or 0.0)
    outcomes = []
    for row in rows.values():
        signals_count = max(1, int(row["signals"]))
        reason_counts = row.pop("reason_counts")
        row["avg_quality_score"] = round(float(row.pop("_quality_sum")) / signals_count, 6)
        row["total_pnl_usd"] = round(float(row["total_pnl_usd"]), 2)
        row["total_r"] = round(float(row["total_r"]), 4)
        row["top_reason_code"] = _top_reason_code(reason_counts)
        outcomes.append(row)
    return sorted(
        outcomes,
        key=lambda row: (int(row["signals"]), float(row["avg_quality_score"])),
        reverse=True,
    )


def _pattern_row(rows: dict[str, dict[str, Any]], pattern: str) -> dict[str, Any]:
    if pattern not in rows:
        rows[pattern] = {
            "pattern": pattern,
            "signals": 0,
            "actionable": 0,
            "submitted": 0,
            "executed": 0,
            "blocked_or_expired": 0,
            "trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "all_closed_trades": 0,
            "shadow_closed": 0,
            "near_miss_closed": 0,
            "ibkr_paper_filled": 0,
            "live": 0,
            "live_filled": 0,
            "degraded_closed": 0,
            "total_pnl_usd": 0.0,
            "total_r": 0.0,
            "_quality_sum": 0.0,
            "reason_counts": {},
        }
    return rows[pattern]


def _top_reason_code(reason_counts: dict[str, int]) -> str:
    if not reason_counts:
        return "none"
    return sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[0][0]
