from __future__ import annotations

from enum import Enum
from typing import Any, Mapping

EVIDENCE_NEAR_MISS_SHADOW = "near_miss_shadow"
EVIDENCE_SHADOW_NO_ORDER = "shadow_no_order"
EVIDENCE_IBKR_PAPER_ORDER = "ibkr_paper_order"
EVIDENCE_IBKR_PAPER_FILL = "ibkr_paper_fill"
EVIDENCE_LIVE_ORDER = "live_order"
EVIDENCE_LIVE_FILL = "live_fill"

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


def evidence_type_for_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
) -> str | None:
    """Return explicit or legacy-inferred evidence type for a signal/trade."""
    metadata = metadata or {}
    explicit = str(metadata.get("evidence_type") or "").strip()
    if explicit in VALID_EVIDENCE_TYPES:
        return _fill_type_for_closed_order(explicit, trade_status)

    if _is_near_miss_shadow(metadata):
        return EVIDENCE_NEAR_MISS_SHADOW
    if _is_no_order_shadow(metadata):
        return EVIDENCE_SHADOW_NO_ORDER

    execution_mode = str(metadata.get("execution_mode") or "").strip()
    ibkr_mode = str(metadata.get("ibkr_mode") or metadata.get("trading_mode") or "").strip()
    if execution_mode == "ibkr" and ibkr_mode == "paper":
        return EVIDENCE_IBKR_PAPER_FILL if _is_closed_status(trade_status) else EVIDENCE_IBKR_PAPER_ORDER
    if execution_mode == "ibkr" and ibkr_mode == "live":
        return EVIDENCE_LIVE_FILL if _is_closed_status(trade_status) else EVIDENCE_LIVE_ORDER
    if execution_mode == "paper":
        return EVIDENCE_IBKR_PAPER_FILL if _is_closed_status(trade_status) else EVIDENCE_IBKR_PAPER_ORDER
    return None


def evidence_quality_for_metadata(metadata: Mapping[str, Any] | None) -> str:
    metadata = metadata or {}
    quality = str(metadata.get("evidence_quality") or "").strip()
    return quality or EVIDENCE_QUALITY_STANDARD


def evidence_type_from_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    status: Any = None,
    trade_status: Any = None,
    signal_metadata: Mapping[str, Any] | None = None,
    broker_order_id: str | None = None,
) -> str | None:
    merged = dict(signal_metadata or {})
    merged.update(dict(metadata or {}))
    if broker_order_id and not merged.get("broker_order_id"):
        merged["broker_order_id"] = broker_order_id
    return evidence_type_for_metadata(merged, trade_status=trade_status if trade_status is not None else status)


def evidence_quality_from_metadata(metadata: Mapping[str, Any] | None) -> str:
    return evidence_quality_for_metadata(metadata)


def with_evidence_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    evidence_type: str | None = None,
    evidence_quality: str | None = None,
    trade_status: Any = None,
    degradation_reason: str | None = None,
) -> dict[str, Any]:
    updated = dict(metadata or {})
    resolved_type = evidence_type or evidence_type_for_metadata(updated, trade_status=trade_status)
    if resolved_type:
        updated["evidence_type"] = resolved_type
    updated["evidence_quality"] = evidence_quality or evidence_quality_for_metadata(updated)
    if degradation_reason:
        updated["evidence_degradation_reason"] = degradation_reason
    return updated


def is_director_review_paper_fill_evidence(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
) -> bool:
    metadata = metadata or {}
    evidence_type = evidence_type_for_metadata(metadata, trade_status=trade_status)
    if evidence_type != EVIDENCE_IBKR_PAPER_FILL:
        return False
    if evidence_quality_for_metadata(metadata) == EVIDENCE_QUALITY_DEGRADED:
        return False
    if _is_near_miss_shadow(metadata) or _is_no_order_shadow(metadata):
        return False
    return True


def is_paper_order_or_fill_evidence(
    metadata: Mapping[str, Any] | None,
    *,
    trade_status: Any = None,
) -> bool:
    metadata = metadata or {}
    evidence_type = evidence_type_for_metadata(metadata, trade_status=trade_status)
    if evidence_type not in {EVIDENCE_IBKR_PAPER_ORDER, EVIDENCE_IBKR_PAPER_FILL}:
        return False
    if evidence_quality_for_metadata(metadata) == EVIDENCE_QUALITY_DEGRADED:
        return False
    if _is_near_miss_shadow(metadata) or _is_no_order_shadow(metadata):
        return False
    return True


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


def _fill_type_for_closed_order(evidence_type: str, trade_status: Any) -> str:
    if not _is_closed_status(trade_status):
        return evidence_type
    if evidence_type == EVIDENCE_IBKR_PAPER_ORDER:
        return EVIDENCE_IBKR_PAPER_FILL
    if evidence_type == EVIDENCE_LIVE_ORDER:
        return EVIDENCE_LIVE_FILL
    return evidence_type


def _is_closed_status(value: Any) -> bool:
    status = str(value.value if hasattr(value, "value") else value or "").strip()
    return status == "closed"
