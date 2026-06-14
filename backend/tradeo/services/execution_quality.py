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

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
from sqlalchemy.orm import Session

from tradeo.db.models import AgentMessageSeverity, AuditLog, Trade
from tradeo.services.evidence import REAL_FILL_PROVENANCE
from tradeo.services.agent_messages import build_idempotency_key, publish_agent_message
from tradeo.services.implementation_shortfall import trade_slippage_r

EXECUTION_QUALITY_METHOD = "fill_vs_signal_eod_v1"
COST_RECALIBRATION_METHOD = "real_fill_cost_recalibration_v1"
DATA_BASIS = "broker_fill_record_eod_daily"
MICROSTRUCTURE_FEED = "none_available"

__all__ = [
    "EXECUTION_QUALITY_METHOD",
    "trade_execution_quality",
    "persist_execution_quality",
    "pattern_execution_quality_summary",
    "COST_RECALIBRATION_METHOD",
    "real_fill_cost_recalibration_report",
    "publish_cost_recalibration_report",
]

ADV_BUCKETS: tuple[dict[str, Any], ...] = (
    {"name": "micro_adv_lt_1m", "min_adv": 0.0, "max_adv": 1_000_000.0, "default_half_spread_bps": 45.0},
    {"name": "thin_adv_1m_5m", "min_adv": 1_000_000.0, "max_adv": 5_000_000.0, "default_half_spread_bps": 20.0},
    {"name": "liquid_adv_5m_25m", "min_adv": 5_000_000.0, "max_adv": 25_000_000.0, "default_half_spread_bps": 8.0},
    {"name": "deep_adv_gte_25m", "min_adv": 25_000_000.0, "max_adv": None, "default_half_spread_bps": 3.0},
)
DEFAULT_COMMISSION_BPS = 0.5


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


def real_fill_cost_recalibration_report(
    trades: Iterable[Trade],
    *,
    min_bucket_samples: int = 3,
    min_total_samples: int = 5,
) -> dict[str, Any]:
    """Advisory tiered-cost recalibration from real broker fills.

    The output is deliberately a suggestion packet. It never mutates live risk,
    strategy config, or the backtest cost function by itself.
    """
    rows = [_cost_recalibration_row(trade) for trade in trades]
    usable = [row for row in rows if row is not None]
    buckets = {
        bucket["name"]: _cost_bucket_summary(
            bucket,
            [row for row in usable if row["adv_bucket"] == bucket["name"]],
            min_bucket_samples=min_bucket_samples,
        )
        for bucket in ADV_BUCKETS
    }
    sufficient_buckets = [
        name for name, bucket in buckets.items() if bucket["sufficient_data"]
    ]
    status = (
        "ok"
        if len(usable) >= int(min_total_samples) and sufficient_buckets
        else "insufficient_real_fill_data"
    )
    report = {
        "method": COST_RECALIBRATION_METHOD,
        "data_basis": DATA_BASIS,
        "microstructure_feed": MICROSTRUCTURE_FEED,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "auto_apply": False,
        "live_risk_config_changed": False,
        "min_total_samples": int(min_total_samples),
        "min_bucket_samples": int(min_bucket_samples),
        "real_fill_sample_count": len(usable),
        "excluded_sample_count": len(rows) - len(usable),
        "sufficient_buckets": sufficient_buckets,
        "buckets": buckets,
        "rows": usable,
        "notes": [
            "Suggestions are advisory only; live risk/order config must be changed through a separate reviewed path.",
            "Recommended half-spread is floored at the existing tier default to avoid underestimating costs from a thin sample.",
        ],
    }
    report["report_hash"] = _stable_hash(
        {key: value for key, value in report.items() if key != "generated_at_utc"}
    )
    return report


def publish_cost_recalibration_report(
    db: Session,
    trades: Iterable[Trade],
    *,
    min_bucket_samples: int = 3,
    min_total_samples: int = 5,
) -> dict[str, Any]:
    """Persist advisory cost-recalibration evidence to agent bus and audit log."""
    report = real_fill_cost_recalibration_report(
        trades,
        min_bucket_samples=min_bucket_samples,
        min_total_samples=min_total_samples,
    )
    severity = (
        AgentMessageSeverity.INFO
        if report["status"] == "ok"
        else AgentMessageSeverity.WARNING
    )
    input_refs = [
        f"trade:{row['trade_id']}"
        for row in report["rows"]
        if row.get("trade_id") is not None
    ]
    message = publish_agent_message(
        db,
        agent="execution_quality",
        payload={
            "kind": "cost_model_recalibration_suggestion",
            "schema_version": 1,
            "data": report,
        },
        severity=severity,
        input_refs=input_refs,
        idempotency_key=build_idempotency_key(
            "execution_quality",
            "cost_model_recalibration_suggestion",
            report["report_hash"],
        ),
    )
    db.add(
        AuditLog(
            actor="execution_quality",
            action="cost_model_recalibration_suggested",
            entity_type="cost_model",
            entity_id=report["report_hash"][:16],
            details_json={
                "report_hash": report["report_hash"],
                "status": report["status"],
                "real_fill_sample_count": report["real_fill_sample_count"],
                "sufficient_buckets": report["sufficient_buckets"],
                "agent_message_id": message.id,
                "auto_apply": False,
                "live_risk_config_changed": False,
            },
        )
    )
    db.commit()
    return {**report, "agent_message_id": message.id}


def _cost_recalibration_row(trade: Trade) -> dict[str, Any] | None:
    quality = trade_execution_quality(trade)
    if quality is None:
        return None
    adv = _extract_avg_dollar_volume(trade)
    bucket = _adv_bucket(adv)
    spread_pct = _extract_spread_observed_pct(trade)
    spread_bps = spread_pct * 10_000.0 if spread_pct is not None else None
    half_spread_bps = spread_bps / 2.0 if spread_bps is not None else None
    entry_slippage_bps = float(quality["entry_slippage_bps"])
    commission_bps = quality.get("commission_bps")
    shortfall = trade_slippage_r(trade)
    risk_per_share = abs(float(trade.entry or 0.0) - float(trade.stop or 0.0))
    entry_slippage_r = quality.get("entry_slippage_r")
    return {
        "trade_id": trade.id,
        "symbol": trade.symbol,
        "adv_bucket": bucket["name"],
        "avg_dollar_volume": None if adv is None else round(float(adv), 4),
        "entry_price": quality["theoretical_entry"],
        "risk_per_share": round(float(risk_per_share), 6),
        "entry_slippage_bps": round(entry_slippage_bps, 6),
        "adverse_entry_slippage_bps": round(max(0.0, entry_slippage_bps), 6),
        "entry_slippage_r": entry_slippage_r,
        "total_slippage_r": None if shortfall is None else shortfall["slippage_r"],
        "spread_observed_pct": None if spread_pct is None else round(float(spread_pct), 8),
        "spread_bps": None if spread_bps is None else round(float(spread_bps), 6),
        "half_spread_bps": None if half_spread_bps is None else round(float(half_spread_bps), 6),
        "commission_bps": None if commission_bps is None else round(float(commission_bps), 6),
        "fill_provenance": quality["fill_provenance"],
    }


def _cost_bucket_summary(
    bucket: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    min_bucket_samples: int,
) -> dict[str, Any]:
    count = len(rows)
    adverse_slippage = [row["adverse_entry_slippage_bps"] for row in rows]
    signed_slippage = [row["entry_slippage_bps"] for row in rows]
    half_spreads = [row["half_spread_bps"] for row in rows if row["half_spread_bps"] is not None]
    commissions = [row["commission_bps"] for row in rows if row["commission_bps"] is not None]
    total_slippage_r = [row["total_slippage_r"] for row in rows if row["total_slippage_r"] is not None]
    sufficient = count >= int(min_bucket_samples)
    observed_half_p75 = _quantile_or_none(half_spreads, 0.75)
    observed_slip_p75 = _quantile_or_none(adverse_slippage, 0.75)
    observed_commission_p75 = _quantile_or_none(commissions, 0.75)
    default_half = float(bucket["default_half_spread_bps"])
    suggestion = None
    if sufficient:
        suggestion = {
            "recommended_half_spread_bps": round(max(default_half, observed_half_p75 or 0.0), 6),
            "recommended_slippage_bps_per_side": round(max(0.0, observed_slip_p75 or 0.0), 6),
            "recommended_commission_bps": round(max(DEFAULT_COMMISSION_BPS, observed_commission_p75 or 0.0), 6),
            "auto_apply": False,
            "live_risk_config_changed": False,
        }
    return {
        "adv_bucket": bucket["name"],
        "adv_min": bucket["min_adv"],
        "adv_max": bucket["max_adv"],
        "count": count,
        "sufficient_data": sufficient,
        "insufficient_reason": None if sufficient else f"needs_{min_bucket_samples}_real_fill_samples",
        "current_default_half_spread_bps": default_half,
        "median_entry_slippage_bps": _median_or_none(signed_slippage),
        "p75_adverse_entry_slippage_bps": observed_slip_p75,
        "median_half_spread_bps": _median_or_none(half_spreads),
        "p75_half_spread_bps": observed_half_p75,
        "median_commission_bps": _median_or_none(commissions),
        "p75_commission_bps": observed_commission_p75,
        "median_total_slippage_r": _median_or_none(total_slippage_r),
        "suggestion": suggestion,
    }


def _extract_avg_dollar_volume(trade: Trade) -> float | None:
    metadata = trade.metadata_json or {}
    signal_metadata = trade.signal.metadata_json if trade.signal is not None else {}
    paths = (
        metadata.get("avg_dollar_volume"),
        _nested(metadata, "signal_snapshot", "features", "avg_dollar_volume"),
        _nested(signal_metadata, "signal_snapshot", "features", "avg_dollar_volume"),
        _nested(signal_metadata, "features", "avg_dollar_volume"),
    )
    return _first_positive_float(paths)


def _extract_spread_observed_pct(trade: Trade) -> float | None:
    metadata = trade.metadata_json or {}
    signal_metadata = trade.signal.metadata_json if trade.signal is not None else {}
    paths = (
        metadata.get("spread_observed_pct"),
        _nested(metadata, "spread_snapshot", "spread_observed_pct"),
        _nested(signal_metadata, "spread_snapshot", "spread_observed_pct"),
        signal_metadata.get("spread_observed_pct"),
    )
    return _first_positive_float(paths)


def _adv_bucket(avg_dollar_volume: float | None) -> dict[str, Any]:
    adv = float(avg_dollar_volume or 0.0)
    for bucket in ADV_BUCKETS:
        max_adv = bucket["max_adv"]
        if adv >= float(bucket["min_adv"]) and (max_adv is None or adv < float(max_adv)):
            return bucket
    return ADV_BUCKETS[-1]


def _nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_positive_float(values: Iterable[Any]) -> float | None:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return None


def _median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(np.median(np.asarray(values, dtype=float))), 6)


def _quantile_or_none(values: list[float], q: float) -> float | None:
    if not values:
        return None
    return round(float(np.quantile(np.asarray(values, dtype=float), q)), 6)


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
