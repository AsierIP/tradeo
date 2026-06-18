from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

EVIDENCE_NEAR_MISS_SHADOW = "near_miss_shadow"
EVIDENCE_SHADOW_NO_ORDER = "shadow_no_order"
EVIDENCE_IBKR_PAPER_ORDER = "ibkr_paper_order"
EVIDENCE_IBKR_PAPER_FILL = "ibkr_paper_fill"
EVIDENCE_LIVE_ORDER = "live_order"
EVIDENCE_LIVE_FILL = "live_fill"

FILL_PROVENANCE_BROKER_EXECUTION = "broker_execution"
FILL_PROVENANCE_BROKER_STATEMENT_IMPORT = "broker_statement_import"
FILL_PROVENANCE_SIMULATED_CLOSE = "simulated_close"
FILL_PROVENANCE_SHADOW_CLOSE = "shadow_close"

EVIDENCE_QUALITY_STANDARD = "standard"
EVIDENCE_QUALITY_DEGRADED = "degraded"

LAB_SHADOW_EXECUTION_MODE = "lab_shadow_observation"


class EvidenceType(str, Enum):
    NEAR_MISS_SHADOW = EVIDENCE_NEAR_MISS_SHADOW
    SHADOW_NO_ORDER = EVIDENCE_SHADOW_NO_ORDER
    IBKR_PAPER_ORDER = EVIDENCE_IBKR_PAPER_ORDER
    IBKR_PAPER_FILL = EVIDENCE_IBKR_PAPER_FILL
    LIVE_ORDER = EVIDENCE_LIVE_ORDER
    LIVE_FILL = EVIDENCE_LIVE_FILL


class EvidenceQuality(str, Enum):
    NORMAL = EVIDENCE_QUALITY_STANDARD
    DEGRADED = EVIDENCE_QUALITY_DEGRADED


class FillProvenance(str, Enum):
    BROKER_EXECUTION = FILL_PROVENANCE_BROKER_EXECUTION
    BROKER_STATEMENT_IMPORT = FILL_PROVENANCE_BROKER_STATEMENT_IMPORT
    SIMULATED_CLOSE = FILL_PROVENANCE_SIMULATED_CLOSE
    SHADOW_CLOSE = FILL_PROVENANCE_SHADOW_CLOSE


VALID_EVIDENCE_TYPES = {
    EVIDENCE_NEAR_MISS_SHADOW,
    EVIDENCE_SHADOW_NO_ORDER,
    EVIDENCE_IBKR_PAPER_ORDER,
    EVIDENCE_IBKR_PAPER_FILL,
    EVIDENCE_LIVE_ORDER,
    EVIDENCE_LIVE_FILL,
}
PAPER_FILL_EVIDENCE_TYPES = {EVIDENCE_IBKR_PAPER_FILL}
SHADOW_EVIDENCE_TYPES = {EVIDENCE_NEAR_MISS_SHADOW, EVIDENCE_SHADOW_NO_ORDER}
FILL_EVIDENCE_TYPES = {EVIDENCE_IBKR_PAPER_FILL, EVIDENCE_LIVE_FILL}
REAL_FILL_PROVENANCE = {
    FILL_PROVENANCE_BROKER_EXECUTION,
    FILL_PROVENANCE_BROKER_STATEMENT_IMPORT,
}
VALID_FILL_PROVENANCE = {
    FILL_PROVENANCE_BROKER_EXECUTION,
    FILL_PROVENANCE_BROKER_STATEMENT_IMPORT,
    FILL_PROVENANCE_SIMULATED_CLOSE,
    FILL_PROVENANCE_SHADOW_CLOSE,
}
STRONG_EVIDENCE_QUALITY = {EVIDENCE_QUALITY_STANDARD, "normal"}

FILL_ID_KEYS = (
    "fill_id",
    "broker_fill_id",
    "ib_fill_id",
    "execution_id",
    "exec_id",
    "ib_exec_id",
    "broker_execution_id",
    "execution_hash",
    "broker_execution_hash",
    "ib_execution_hash",
    "fill_id_hash",
    "entry_fill_id_hash",
    "exit_fill_id_hash",
    "entry_broker_execution_hash",
    "exit_broker_execution_hash",
)
BROKER_TIMESTAMP_KEYS = (
    "broker_execution_time",
    "ib_execution_time",
    "broker_executed_at",
    "execution_time",
    "executed_at",
    "fill_time",
    "broker_fill_time",
    "statement_execution_time",
    "entry_broker_execution_time",
    "exit_broker_execution_time",
)
COMMISSION_KEYS = (
    "commission",
    "commission_usd",
    "broker_commission",
    "ib_commission",
    "fees",
    "other_fees",
)
EVIDENCE_NESTED_METADATA_KEYS = (
    "broker_execution",
    "execution",
    "execution_report",
    "execution_observation",
    "broker_statement",
    "statement_row",
)


def evidence_type_for_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
) -> str | None:
    """Return explicit or legacy-inferred evidence type for a signal/trade."""
    metadata = metadata or {}
    explicit = str(metadata.get("evidence_type") or "").strip()
    if explicit in VALID_EVIDENCE_TYPES:
        return _fill_type_for_closed_order(explicit, trade_status, metadata)

    if _is_near_miss_shadow(metadata):
        return EVIDENCE_NEAR_MISS_SHADOW
    if _is_no_order_shadow(metadata):
        return EVIDENCE_SHADOW_NO_ORDER

    execution_mode = str(metadata.get("execution_mode") or "").strip()
    ibkr_mode = str(metadata.get("ibkr_mode") or metadata.get("trading_mode") or "").strip()
    if execution_mode == "ibkr" and ibkr_mode == "paper":
        return (
            EVIDENCE_IBKR_PAPER_FILL
            if _can_promote_closed_order_to_fill(trade_status, metadata)
            else EVIDENCE_IBKR_PAPER_ORDER
        )
    if execution_mode == "ibkr" and ibkr_mode == "live":
        return (
            EVIDENCE_LIVE_FILL
            if _can_promote_closed_order_to_fill(trade_status, metadata)
            else EVIDENCE_LIVE_ORDER
        )
    if execution_mode == "paper":
        return (
            EVIDENCE_IBKR_PAPER_FILL
            if _can_promote_closed_order_to_fill(trade_status, metadata)
            else EVIDENCE_IBKR_PAPER_ORDER
        )
    if metadata.get("broker_order_id") or metadata.get("parent_order_id"):
        return (
            EVIDENCE_IBKR_PAPER_FILL
            if _can_promote_closed_order_to_fill(trade_status, metadata)
            else EVIDENCE_IBKR_PAPER_ORDER
        )
    return None


def evidence_quality_for_metadata(metadata: Mapping[str, Any] | None) -> str:
    metadata = metadata or {}
    quality = str(metadata.get("evidence_quality") or "").strip()
    if quality == "normal":
        return EVIDENCE_QUALITY_STANDARD
    return quality or EVIDENCE_QUALITY_STANDARD


def fill_provenance_for_metadata(metadata: Mapping[str, Any] | None) -> str | None:
    metadata = metadata or {}
    provenance = str(metadata.get("fill_provenance") or "").strip()
    if provenance in VALID_FILL_PROVENANCE:
        return provenance
    if _is_near_miss_shadow(metadata) or _is_no_order_shadow(metadata):
        return FILL_PROVENANCE_SHADOW_CLOSE
    return None


def evidence_type_from_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    status: Any = None,
    trade_status: Any = None,
    signal_metadata: Mapping[str, Any] | None = None,
    broker_order_id: str | None = None,
    stored_evidence_type: str | None = None,
    stored_evidence_quality: str | None = None,
) -> str | None:
    merged = dict(signal_metadata or {})
    merged.update(dict(metadata or {}))
    if stored_evidence_type and not merged.get("evidence_type"):
        merged["evidence_type"] = stored_evidence_type
    if stored_evidence_quality and not merged.get("evidence_quality"):
        merged["evidence_quality"] = stored_evidence_quality
    if broker_order_id and not merged.get("broker_order_id"):
        merged["broker_order_id"] = broker_order_id
    return evidence_type_for_metadata(merged, trade_status=trade_status if trade_status is not None else status)


def evidence_quality_from_metadata(metadata: Mapping[str, Any] | None) -> str:
    return evidence_quality_for_metadata(metadata)


def evidence_metadata_with_stored_columns(
    metadata: Mapping[str, Any] | None,
    *,
    evidence_type: str | None = None,
    evidence_quality: str | None = None,
) -> dict[str, Any]:
    updated = dict(metadata or {})
    if evidence_type and not updated.get("evidence_type"):
        updated["evidence_type"] = evidence_type
    if evidence_quality and not updated.get("evidence_quality"):
        updated["evidence_quality"] = evidence_quality
    return updated


def with_evidence_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    evidence_type: str | None = None,
    evidence_quality: str | None = None,
    fill_provenance: str | None = None,
    trade_status: Any = None,
    degradation_reason: str | None = None,
) -> dict[str, Any]:
    updated = dict(metadata or {})
    resolved_type = evidence_type or evidence_type_for_metadata(updated, trade_status=trade_status)
    if resolved_type:
        updated["evidence_type"] = resolved_type
    updated["evidence_quality"] = evidence_quality or evidence_quality_for_metadata(updated)
    if fill_provenance:
        updated["fill_provenance"] = fill_provenance
    if degradation_reason:
        updated["evidence_degradation_reason"] = degradation_reason
    return updated


def is_director_review_paper_fill_evidence(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
    signal_metadata: Mapping[str, Any] | None = None,
    broker_order_id: str | None = None,
) -> bool:
    return is_strong_fill_evidence(
        metadata,
        trade_status=trade_status,
        signal_metadata=signal_metadata,
        broker_order_id=broker_order_id,
        allowed_evidence_types=PAPER_FILL_EVIDENCE_TYPES,
    )


def is_paper_order_or_fill_evidence(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
    signal_metadata: Mapping[str, Any] | None = None,
    broker_order_id: str | None = None,
) -> bool:
    metadata = dict(signal_metadata or {}) | dict(metadata or {})
    if broker_order_id and not metadata.get("broker_order_id"):
        metadata["broker_order_id"] = broker_order_id
    evidence_type = evidence_type_for_metadata(metadata, trade_status=trade_status)
    if evidence_type not in {EVIDENCE_IBKR_PAPER_ORDER, EVIDENCE_IBKR_PAPER_FILL}:
        return False
    if evidence_quality_for_metadata(metadata) == EVIDENCE_QUALITY_DEGRADED:
        return False
    if _is_near_miss_shadow(metadata) or _is_no_order_shadow(metadata):
        return False
    if evidence_type == EVIDENCE_IBKR_PAPER_FILL:
        return is_strong_fill_evidence(
            metadata,
            trade_status=trade_status,
            allowed_evidence_types=PAPER_FILL_EVIDENCE_TYPES,
        )
    if _is_closed_status(trade_status):
        return False
    return True


def is_strong_fill_evidence(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
    signal_metadata: Mapping[str, Any] | None = None,
    broker_order_id: str | None = None,
    allowed_evidence_types: set[str] | None = None,
) -> bool:
    merged = dict(signal_metadata or {}) | dict(metadata or {})
    if broker_order_id and not merged.get("broker_order_id"):
        merged["broker_order_id"] = broker_order_id
    evidence_type = evidence_type_for_metadata(merged, trade_status=trade_status)
    allowed = allowed_evidence_types or FILL_EVIDENCE_TYPES
    if evidence_type not in allowed:
        return False
    if evidence_quality_for_metadata(merged) not in STRONG_EVIDENCE_QUALITY:
        return False
    if fill_provenance_for_metadata(merged) not in REAL_FILL_PROVENANCE:
        return False
    if _is_near_miss_shadow(merged) or _is_no_order_shadow(merged):
        return False
    return (
        _has_any_metadata_value(merged, FILL_ID_KEYS)
        and _has_any_metadata_value(merged, BROKER_TIMESTAMP_KEYS)
        and _has_any_metadata_value(merged, COMMISSION_KEYS)
    )


def evidence_type_counts(
    items: list[Mapping[str, Any] | None],
    *,
    trade_statuses: list[Any] | None = None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for index, metadata in enumerate(items):
        trade_status = trade_statuses[index] if trade_statuses is not None and index < len(trade_statuses) else None
        evidence_type = evidence_type_for_metadata(metadata, trade_status=trade_status) or "unknown"
        counts[evidence_type] = counts.get(evidence_type, 0) + 1
    return counts


def evidence_quality_counts(items: list[Mapping[str, Any] | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for metadata in items:
        quality = evidence_quality_for_metadata(metadata)
        counts[quality] = counts.get(quality, 0) + 1
    return counts


def _is_near_miss_shadow(metadata: Mapping[str, Any]) -> bool:
    return bool(metadata.get("near_miss_shadow")) or (
        bool(metadata.get("near_miss")) and bool(metadata.get("no_ibkr_order"))
    )


def _is_no_order_shadow(metadata: Mapping[str, Any]) -> bool:
    return (
        bool(metadata.get("no_ibkr_order"))
        or bool(metadata.get("observation_only"))
        or str(metadata.get("execution_mode") or "") == LAB_SHADOW_EXECUTION_MODE
    )


def _fill_type_for_closed_order(
    evidence_type: str,
    trade_status: Any,
    metadata: Mapping[str, Any],
) -> str:
    if not _is_closed_status(trade_status):
        return evidence_type
    if fill_provenance_for_metadata(metadata) not in REAL_FILL_PROVENANCE:
        return evidence_type
    if evidence_type == EVIDENCE_IBKR_PAPER_ORDER:
        return EVIDENCE_IBKR_PAPER_FILL
    if evidence_type == EVIDENCE_LIVE_ORDER:
        return EVIDENCE_LIVE_FILL
    return evidence_type


def _can_promote_closed_order_to_fill(trade_status: Any, metadata: Mapping[str, Any]) -> bool:
    return _is_closed_status(trade_status) and fill_provenance_for_metadata(metadata) in REAL_FILL_PROVENANCE


def _is_closed_status(value: Any) -> bool:
    status = str(value.value if hasattr(value, "value") else value or "").strip()
    return status == "closed"


def _has_any_metadata_value(metadata: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    for source in _metadata_sources(metadata):
        for key in keys:
            value = source.get(key)
            if value is not None and str(value).strip() != "":
                return True
    return False


def _metadata_sources(metadata: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = [metadata]
    for key in EVIDENCE_NESTED_METADATA_KEYS:
        value = metadata.get(key)
        if isinstance(value, Mapping):
            sources.append(value)
    ibkr_fills = metadata.get("ibkr_fills")
    if isinstance(ibkr_fills, list):
        sources.extend(value for value in ibkr_fills if isinstance(value, Mapping))
    return sources
