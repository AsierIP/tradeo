from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from tradeo.db.models import AuditLog, DiscoveredPattern, DiscoveredPatternMatch, Signal, Trade
from tradeo.services.evidence import evidence_metadata_with_stored_columns, is_paper_order_or_fill_evidence

REJECTION_ACTIONS = {
    "entry_match_rejected_by_entry_gate": "entry_gate",
    "entry_match_rejected_by_quality": "entry_quality",
    "entry_match_rejected_by_risk": "risk",
    "entry_match_skipped_by_cooldown": "cooldown",
}


def laboratory_diagnostics(db: Session, *, limit: int = 24) -> dict[str, Any]:
    """Read-only presentation payload for Lab candidate and near-miss diagnostics."""
    limit = max(1, min(limit, 100))
    rows = _dedupe_rows(
        [
            *_signal_rows(db, max_rows=max(limit * 4, 80)),
            *_rejection_rows(db, max_rows=max(limit * 6, 120)),
        ],
        _shadow_match_rows(db, max_rows=max(limit * 4, 80)),
    )
    patterns = _patterns_by_id(db, rows)
    history = _paper_history_index(db)
    enriched = [_enrich_row(row, patterns, history) for row in rows]
    enriched.sort(key=_sort_key, reverse=True)
    visible = enriched[:limit]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "candidates": sum(1 for row in enriched if row["source"] == "candidate_signal"),
            "rejected": sum(1 for row in enriched if row["source"] == "rejected"),
            "shadow_near_misses": sum(1 for row in enriched if row["source"] == "shadow_match"),
            "with_paper_history": sum(
                1 for row in enriched if row["paper_history"]["closed_trades"] > 0
            ),
            "entry_gate_failures": sum(
                1
                for row in enriched
                if row.get("entry_gate", {}).get("passed") is False
                or row.get("rejection_stage") == "entry_gate"
            ),
            "returned": len(visible),
            "available": len(enriched),
        },
        "opportunities": visible,
    }


def _signal_rows(db: Session, *, max_rows: int) -> list[dict[str, Any]]:
    signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(max_rows * 3).all()
    rows: list[dict[str, Any]] = []
    for signal in signals:
        if len(rows) >= max_rows:
            break
        if not _is_laboratory_signal(signal):
            continue
        metadata = signal.metadata_json or {}
        if not any(
            key in metadata for key in ("match", "entry_gate", "entry_quality", "opportunity_rank")
        ):
            continue
        match = _dict(metadata.get("match"))
        snapshot = _dict(metadata.get("signal_snapshot"))
        entry_gate = _first_dict(
            metadata.get("entry_gate"),
            _dict(match.get("metrics")).get("entry_gate"),
            snapshot.get("entry_gate"),
        )
        entry_quality = _first_dict(metadata.get("entry_quality"), snapshot.get("entry_quality"))
        row = _base_match_row(
            source="candidate_signal",
            status=_status_value(signal.status),
            symbol=signal.symbol,
            pattern=signal.pattern,
            pattern_id=_safe_int(metadata.get("pattern_id") or match.get("pattern_id")),
            side=signal.side,
            timeframe=signal.timeframe,
            entry_variant_id=str(metadata.get("entry_variant_id") or match.get("entry_variant_id") or ""),
            entry_variant=_first_dict(metadata.get("entry_variant"), match.get("entry_variant")),
            regime=_first_dict(metadata.get("regime"), match.get("regime"), snapshot.get("regime")),
            regime_fit=_first_dict(
                metadata.get("regime_fit"), match.get("regime_fit"), snapshot.get("regime_fit")
            ),
            rank=metadata.get("opportunity_rank"),
            rank_score=metadata.get("opportunity_rank_score"),
            rank_components=_dict(metadata.get("opportunity_rank_components")),
            score=match.get("score", signal.composite_score),
            entry_score=entry_gate.get("entry_score", signal.composite_score),
            similarity=match.get("similarity"),
            entry_gate=entry_gate,
            entry_quality=entry_quality,
            rejection_stage=None,
            rejection_reason=_candidate_reason(signal, entry_quality),
            event_at=signal.created_at,
            window_end=str(match.get("window_end") or ""),
            source_id=signal.id,
        )
        rows.append(row)
    return rows


def _rejection_rows(db: Session, *, max_rows: int) -> list[dict[str, Any]]:
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.actor == "laboratory")
        .filter(AuditLog.action.in_(list(REJECTION_ACTIONS)))
        .order_by(AuditLog.timestamp.desc())
        .limit(max_rows)
        .all()
    )
    rows: list[dict[str, Any]] = []
    for log in logs:
        details = log.details_json or {}
        match = _dict(details.get("match"))
        metrics = _dict(match.get("metrics"))
        entry_gate = _first_dict(details.get("entry_gate"), metrics.get("entry_gate"))
        entry_quality = _dict(details.get("entry_quality"))
        risk = _dict(details.get("risk"))
        row = _base_match_row(
            source="rejected",
            status=log.action,
            symbol=str(match.get("symbol") or ""),
            pattern=str(match.get("pattern_name") or match.get("pattern") or ""),
            pattern_id=_safe_int(match.get("pattern_id") or log.entity_id),
            side=str(match.get("side") or ""),
            timeframe=str(match.get("timeframe") or ""),
            entry_variant_id=str(match.get("entry_variant_id") or metrics.get("entry_variant_id") or ""),
            entry_variant=_first_dict(match.get("entry_variant"), metrics.get("entry_variant")),
            regime=_first_dict(match.get("regime"), metrics.get("regime")),
            regime_fit=_first_dict(match.get("regime_fit"), metrics.get("regime_fit")),
            rank=match.get("opportunity_rank"),
            rank_score=match.get("opportunity_rank_score"),
            rank_components=_dict(match.get("opportunity_rank_components")),
            score=match.get("score"),
            entry_score=match.get("entry_score", entry_gate.get("entry_score")),
            similarity=match.get("similarity"),
            entry_gate=entry_gate,
            entry_quality=entry_quality,
            rejection_stage=REJECTION_ACTIONS.get(log.action, "unknown"),
            rejection_reason=_rejection_reason(log.action, entry_gate, entry_quality, risk, details),
            event_at=log.timestamp,
            window_end=str(match.get("window_end") or ""),
            source_id=log.id,
        )
        rows.append(row)
    return rows


def _shadow_match_rows(db: Session, *, max_rows: int) -> list[dict[str, Any]]:
    matches = (
        db.query(DiscoveredPatternMatch)
        .options(joinedload(DiscoveredPatternMatch.pattern))
        .filter(DiscoveredPatternMatch.status.in_(["lab_entry_candidate", "lab_watchlist"]))
        .order_by(DiscoveredPatternMatch.matched_at.desc(), DiscoveredPatternMatch.score.desc())
        .limit(max_rows)
        .all()
    )
    rows: list[dict[str, Any]] = []
    for match in matches:
        metrics = match.metrics_json or {}
        entry_gate = _dict(metrics.get("entry_gate"))
        pattern = match.pattern
        pattern_name = pattern.name if pattern is not None else f"pattern_{match.pattern_id}"
        row = _base_match_row(
            source="shadow_match",
            status=match.status,
            symbol=match.symbol,
            pattern=pattern_name,
            pattern_id=match.pattern_id,
            side=match.side,
            timeframe=match.timeframe,
            entry_variant_id=str(metrics.get("entry_variant_id") or ""),
            entry_variant=_dict(metrics.get("entry_variant")),
            regime=_dict(metrics.get("regime")),
            regime_fit=_dict(metrics.get("regime_fit")),
            rank=None,
            rank_score=None,
            rank_components={},
            score=match.score,
            entry_score=entry_gate.get("entry_score"),
            similarity=match.similarity,
            entry_gate=entry_gate,
            entry_quality={},
            rejection_stage="shadow_near_miss",
            rejection_reason=_shadow_reason(entry_gate),
            event_at=match.matched_at,
            window_end=match.window_end,
            source_id=match.id,
        )
        rows.append(row)
    return rows


def _base_match_row(**values: Any) -> dict[str, Any]:
    variant = _dict(values.get("entry_variant"))
    regime = _dict(values.get("regime"))
    return {
        "source": values["source"],
        "status": values.get("status") or "",
        "symbol": values.get("symbol") or "",
        "pattern": values.get("pattern") or "",
        "pattern_id": values.get("pattern_id"),
        "side": values.get("side") or "",
        "timeframe": values.get("timeframe") or "",
        "entry_variant_id": values.get("entry_variant_id") or "",
        "entry_variant_label": _variant_label(variant, values.get("entry_variant_id")),
        "regime_key": str(regime.get("regime_key") or ""),
        "rank": _safe_int(values.get("rank")),
        "rank_score": _safe_float(values.get("rank_score")),
        "score": _safe_float(values.get("score")),
        "entry_score": _safe_float(values.get("entry_score")),
        "similarity": _safe_float(values.get("similarity")),
        "opportunity_rank_components": _clean_dict(values.get("rank_components")),
        "entry_gate": _clean_dict(values.get("entry_gate")),
        "entry_quality": _clean_dict(values.get("entry_quality")),
        "regime_fit": _clean_dict(values.get("regime_fit")),
        "rejection_stage": values.get("rejection_stage"),
        "rejection_reason": values.get("rejection_reason") or "",
        "created_at": _iso(values.get("event_at")),
        "window_end": values.get("window_end") or "",
        "_source_id": values.get("source_id"),
    }


def _enrich_row(
    row: dict[str, Any],
    patterns: dict[int, DiscoveredPattern],
    history_index: dict[str, Any],
) -> dict[str, Any]:
    pattern = patterns.get(int(row["pattern_id"])) if row.get("pattern_id") is not None else None
    history = _paper_history_for(row, history_index)
    missing = _missing_to_promote(pattern, history)
    return {
        **{key: value for key, value in row.items() if not key.startswith("_")},
        "entry_gate_components": _entry_gate_components(row.get("entry_gate") or {}),
        "paper_history": history,
        "promotion": _promotion_payload(pattern, missing),
        "missing_to_promote": missing,
    }


def _dedupe_rows(
    primary_rows: list[dict[str, Any]],
    shadow_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for row in [*primary_rows, *shadow_rows]:
        key = _dedupe_key(row)
        if row["source"] == "shadow_match" and key in seen:
            continue
        seen.add(key)
        rows.append(row)
    return rows


def _dedupe_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("symbol"),
        row.get("pattern_id"),
        row.get("entry_variant_id"),
        row.get("window_end") or row.get("_source_id"),
    )


def _patterns_by_id(db: Session, rows: list[dict[str, Any]]) -> dict[int, DiscoveredPattern]:
    pattern_ids = sorted({int(row["pattern_id"]) for row in rows if row.get("pattern_id") is not None})
    if not pattern_ids:
        return {}
    return {
        pattern.id: pattern
        for pattern in db.query(DiscoveredPattern).filter(DiscoveredPattern.id.in_(pattern_ids)).all()
    }


def _paper_history_index(db: Session) -> dict[str, Any]:
    trades = (
        db.query(Trade)
        .options(joinedload(Trade.signal))
        .order_by(Trade.opened_at.desc())
        .limit(800)
        .all()
    )
    by_id: dict[int, list[Trade]] = defaultdict(list)
    by_name: dict[str, list[Trade]] = defaultdict(list)
    for trade in trades:
        signal = trade.signal
        if signal is not None:
            if not _is_laboratory_signal(signal):
                continue
            metadata = signal.metadata_json or {}
        else:
            metadata = trade.metadata_json or {}
            if not _is_laboratory_trade_metadata(metadata):
                continue
        trade_metadata = evidence_metadata_with_stored_columns(
            trade.metadata_json or {},
            evidence_type=trade.evidence_type,
            evidence_quality=trade.evidence_quality,
        )
        if not is_paper_order_or_fill_evidence(
            trade_metadata,
            trade_status=trade.status,
            signal_metadata=(signal.metadata_json if signal is not None else {}) or {},
            broker_order_id=trade.broker_order_id,
        ):
            continue
        pattern_id = _safe_int(metadata.get("pattern_id"))
        if pattern_id is not None:
            by_id[pattern_id].append(trade)
        by_name[str(trade.pattern)].append(trade)
    return {"by_id": by_id, "by_name": by_name}


def _paper_history_for(row: dict[str, Any], history_index: dict[str, Any]) -> dict[str, Any]:
    pattern_id = row.get("pattern_id")
    trades: list[Trade] = []
    if pattern_id is not None:
        trades = list(history_index["by_id"].get(int(pattern_id), []))
    if not trades and row.get("pattern"):
        trades = list(history_index["by_name"].get(str(row["pattern"]), []))
    closed = [trade for trade in trades if _status_value(trade.status) == "closed"]
    open_trades = [trade for trade in trades if _status_value(trade.status) == "open"]
    r_values = [float(trade.r_multiple or 0.0) for trade in closed]
    wins = [value for value in r_values if value > 0]
    losses = [abs(value) for value in r_values if value < 0]
    variant = str(row.get("entry_variant_id") or "")
    regime = str(row.get("regime_key") or "")
    return {
        "closed_trades": len(closed),
        "open_trades": len(open_trades),
        "total_r": round(sum(r_values), 4),
        "expectancy_r": round(sum(r_values) / len(r_values), 4) if r_values else 0.0,
        "win_rate": round(len(wins) / len(r_values), 4) if r_values else 0.0,
        "profit_factor": round(sum(wins) / sum(losses), 4) if losses else round(sum(wins), 4),
        "unique_symbols": len({trade.symbol for trade in closed}),
        "unique_days": len(
            {
                (trade.closed_at or trade.opened_at).date().isoformat()
                for trade in closed
                if trade.closed_at or trade.opened_at
            }
        ),
        "variant_closed_trades": sum(1 for trade in closed if _trade_variant(trade) == variant),
        "regime_closed_trades": sum(1 for trade in closed if _trade_regime(trade) == regime),
        "last_trade_status": _status_value(trades[0].status) if trades else None,
    }


def _missing_to_promote(
    pattern: DiscoveredPattern | None,
    history: dict[str, Any],
) -> list[str]:
    if pattern is None:
        return ["missing_pattern_record"]
    status = _status_value(pattern.status)
    if status == "production":
        return []
    lab_execution = _dict((pattern.metrics_json or {}).get("lab_execution"))
    blockers = [str(item) for item in lab_execution.get("promotion_blockers", []) if item]
    if blockers:
        return blockers
    if lab_execution.get("eligible_for_director_review") is True:
        return ["ready_for_director_review"]

    missing: list[str] = []
    if int(history["closed_trades"]) < 10:
        missing.append("closed_lab_trades_below_10")
    if int(history["unique_symbols"]) < 3:
        missing.append("unique_lab_symbols_below_3")
    if int(history["unique_days"]) < 3:
        missing.append("unique_lab_days_below_3")
    if int(history["closed_trades"]) > 0 and float(history["expectancy_r"]) < 0:
        missing.append("lab_expectancy_below_0.0r")
    if int(history["closed_trades"]) > 0 and float(history["profit_factor"]) < 1.2:
        missing.append("lab_profit_factor_below_1.2")
    if not missing:
        missing.append("needs_director_review_refresh")
    return missing


def _promotion_payload(pattern: DiscoveredPattern | None, missing: list[str]) -> dict[str, Any]:
    if pattern is None:
        return {
            "pattern_status": "unknown",
            "promotion_status": "unknown",
            "promotion_reason": "",
            "eligible_for_director_review": False,
            "blockers": missing,
        }
    lab_execution = _dict((pattern.metrics_json or {}).get("lab_execution"))
    return {
        "pattern_status": _status_value(pattern.status),
        "promotion_status": pattern.promotion_status,
        "promotion_reason": pattern.promotion_reason,
        "eligible_for_director_review": bool(lab_execution.get("eligible_for_director_review", False)),
        "blockers": missing,
    }


def _entry_gate_components(entry_gate: dict[str, Any]) -> list[dict[str, Any]]:
    if not entry_gate:
        return []
    trigger = str(entry_gate.get("trigger") or "")
    return [
        {
            "name": "trigger",
            "value": trigger or None,
            "ok": trigger not in {"", "no_operational_trigger", "insufficient_history"},
        },
        {
            "name": "volume",
            "value": _safe_float(entry_gate.get("volume_ratio")),
            "ok": _optional_bool(entry_gate.get("volume_confirmed")),
        },
        {
            "name": "regime",
            "value": _safe_float(entry_gate.get("regime_score")),
            "ok": _optional_bool(entry_gate.get("regime_ok")),
        },
        {
            "name": "extension",
            "value": _safe_float(entry_gate.get("extension_atr")),
            "ok": _optional_bool(entry_gate.get("not_extended")),
        },
        {
            "name": "trend",
            "value": "aligned" if entry_gate.get("trend_aligned") is True else "off",
            "ok": _optional_bool(entry_gate.get("trend_aligned")),
        },
        {
            "name": "atr",
            "value": _safe_float(entry_gate.get("atr_pct")),
            "ok": _optional_bool(entry_gate.get("volatility_ok")),
        },
    ]


def _candidate_reason(signal: Signal, entry_quality: dict[str, Any]) -> str:
    flags = [str(item) for item in entry_quality.get("flags", []) if item]
    if flags:
        return ", ".join(flags)
    if signal.human_approved:
        return "paper_execution_requested"
    return "paper_candidate_not_submitted"


def _rejection_reason(
    action: str,
    entry_gate: dict[str, Any],
    entry_quality: dict[str, Any],
    risk: dict[str, Any],
    details: dict[str, Any],
) -> str:
    if action == "entry_match_rejected_by_entry_gate":
        blockers = []
        if entry_gate.get("trigger") in {"no_operational_trigger", "insufficient_history"}:
            blockers.append(str(entry_gate.get("trigger")))
        if entry_gate.get("volume_confirmed") is False:
            blockers.append("weak_volume_confirmation")
        if entry_gate.get("regime_ok") is False:
            blockers.append("regime_filter_failed")
        if entry_gate.get("not_extended") is False:
            blockers.append("overextended")
        return ", ".join(blockers) or str(entry_gate.get("reason") or "entry_gate_failed")
    if action == "entry_match_rejected_by_quality":
        flags = [str(item) for item in entry_quality.get("flags", []) if item]
        return ", ".join(flags) or "entry_quality_below_threshold"
    if action == "entry_match_rejected_by_risk":
        hard = [str(item) for item in risk.get("hard_rejections", []) if item]
        return ", ".join(hard) or str(risk.get("reason") or "risk_rejected")
    if action == "entry_match_skipped_by_cooldown":
        return f"cooldown_{details.get('cooldown_minutes', '?')}_minutes"
    return action


def _shadow_reason(entry_gate: dict[str, Any]) -> str:
    if entry_gate.get("passed") is False:
        return _rejection_reason("entry_match_rejected_by_entry_gate", entry_gate, {}, {}, {})
    return "stored_match_without_signal"


def _is_laboratory_signal(signal: Signal) -> bool:
    metadata = signal.metadata_json or {}
    if metadata.get("entry_module") == "laboratory":
        return True
    purpose = str(metadata.get("purpose") or "")
    return signal.strategy_version.startswith(("laboratory_", "ibkr_paper_", "ibkr_smoke_")) or (
        purpose.startswith("ibkr_paper_")
    )


def _is_laboratory_trade_metadata(metadata: dict[str, Any]) -> bool:
    return (
        metadata.get("entry_module") == "laboratory"
        or metadata.get("source_module") == "laboratory"
        or metadata.get("execution_mode") == "paper"
        or metadata.get("ibkr_mode") == "paper"
    )


def _trade_variant(trade: Trade) -> str:
    metadata = (trade.signal.metadata_json if trade.signal is not None else {}) or {}
    return str(metadata.get("entry_variant_id") or "")


def _trade_regime(trade: Trade) -> str:
    metadata = (trade.signal.metadata_json if trade.signal is not None else {}) or {}
    return str((_dict(metadata.get("regime"))).get("regime_key") or "")


def _sort_key(row: dict[str, Any]) -> tuple[float, float, float]:
    opportunity_score = row.get("rank_score")
    if opportunity_score is None:
        opportunity_score = row.get("score") or row.get("entry_score") or 0.0
    source_weight = {"candidate_signal": 0.03, "rejected": 0.02, "shadow_match": 0.01}.get(
        row["source"], 0.0
    )
    return (float(opportunity_score or 0.0), source_weight, _timestamp(row.get("created_at")))


def _variant_label(variant: dict[str, Any], variant_id: Any) -> str:
    return str(
        variant.get("label")
        or variant.get("name")
        or variant.get("order_style")
        or variant.get("id")
        or variant_id
        or ""
    )


def _first_dict(*values: Any) -> dict[str, Any]:
    for value in values:
        item = _dict(value)
        if item:
            return item
    return {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_dict(value: Any) -> dict[str, Any]:
    item = _dict(value)
    return {str(key): _clean_value(value) for key, value in item.items()}


def _clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _status_value(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "")


def _timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0.0
