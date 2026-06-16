from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus

PRODUCTION_MANIFEST_KEY = "production_manifest"
PRODUCTION_MANIFEST_SCHEMA = "tradeo.production_manifest.v1"
PRODUCTION_MANIFEST_HASH_ALGORITHM = "sha256_canonical_v1"
PRODUCTION_GATE_SCOPE = "director_production_gate"
_HASH_KEYS = {"hash", "manifest_hash", "sha256"}


def build_production_manifest(
    pattern: DiscoveredPattern | None = None,
    *,
    version: str | None = None,
    reviewer: str,
    evidence_packet: dict[str, Any],
    expires_at: datetime | str | None = None,
    approved_at: datetime | str | None = None,
    approved_by: str = "director",
) -> dict[str, Any]:
    """Build the canonical manifest Fox Hunter requires for production patterns."""

    approved_time = _parse_datetime(approved_at or datetime.now(timezone.utc)) or datetime.now(timezone.utc)
    expires = _parse_datetime(expires_at) if expires_at is not None else approved_time + timedelta(days=90)
    normalized_packet = _normalized_evidence_packet(pattern, evidence_packet)
    manifest = {
        "schema": PRODUCTION_MANIFEST_SCHEMA,
        "version": str(version or _default_manifest_version(pattern, approved_time)),
        "status": "approved",
        "approved": True,
        "approved_by": approved_by,
        "reviewer": reviewer,
        "approved_at": approved_time.isoformat(),
        "expires_at": (expires or approved_time).isoformat(),
        "evidence_packet": normalized_packet,
        "hash_algorithm": PRODUCTION_MANIFEST_HASH_ALGORITHM,
    }
    manifest["manifest_hash"] = production_manifest_hash(manifest)
    return manifest


def production_manifest_hash(manifest: dict[str, Any]) -> str:
    payload = _canonical_manifest_payload(manifest)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def production_manifest_status(
    pattern: DiscoveredPattern | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = now or datetime.now(timezone.utc)
    if pattern is None:
        return _status(False, "missing_pattern", checked_at)
    pattern_status = _status_value(pattern.status)
    if pattern_status != DiscoveredPatternStatus.PRODUCTION.value:
        return _status(False, "pattern_not_production", checked_at, pattern_status=pattern_status)
    manifest = _manifest_from_pattern(pattern)
    if not isinstance(manifest, dict) or not manifest:
        return _status(False, "missing_production_manifest", checked_at, pattern_status=pattern_status)

    errors: list[str] = []
    manifest_schema = str(manifest.get("schema") or "").strip()
    if manifest_schema != PRODUCTION_MANIFEST_SCHEMA:
        errors.append(
            "missing_manifest_schema"
            if not manifest_schema
            else "unsupported_manifest_schema"
        )
    manifest_status = str(manifest.get("status") or "").lower()
    approved = manifest.get("approved") is True and manifest_status == "approved"
    if not approved:
        errors.append("manifest_not_approved")
    if not str(manifest.get("version") or "").strip():
        errors.append("missing_manifest_version")
    if str(manifest.get("approved_by") or "").lower() != "director":
        errors.append("missing_director_approval")
    reviewer = str(manifest.get("reviewer") or manifest.get("reviewed_by") or "").strip()
    if not reviewer:
        errors.append("missing_reviewer")
    expires_at = _parse_datetime(manifest.get("expires_at"))
    if expires_at is None:
        errors.append("missing_expiry")
    elif expires_at <= checked_at:
        errors.append("manifest_expired")
    manifest_hash = _manifest_hash(manifest)
    hash_algorithm = str(manifest.get("hash_algorithm") or "").strip()
    if not manifest_hash:
        errors.append("missing_manifest_hash")
    evidence_packet_errors = _evidence_packet_errors(manifest)
    errors.extend(evidence_packet_errors)
    if hash_algorithm != PRODUCTION_MANIFEST_HASH_ALGORITHM:
        errors.append("unsupported_manifest_hash_algorithm")
    elif manifest_hash and production_manifest_hash(manifest) != manifest_hash:
        errors.append("manifest_hash_mismatch")

    valid = not errors
    return _status(
        valid,
        "valid" if valid else errors[0],
        checked_at,
        pattern_status=pattern_status,
        version=str(manifest.get("version") or ""),
        reviewer=reviewer,
        approved_by=str(manifest.get("approved_by") or ""),
        expires_at=expires_at.isoformat() if expires_at is not None else None,
        schema=manifest_schema,
        manifest_hash=manifest_hash,
        evidence_packet=_evidence_packet_summary(manifest),
        evidence_packet_complete=not evidence_packet_errors,
        hash_algorithm=hash_algorithm,
        hash_verified=valid and hash_algorithm == PRODUCTION_MANIFEST_HASH_ALGORITHM,
        errors=errors,
    )


def production_manifest_for_pattern(pattern: DiscoveredPattern | None) -> dict[str, Any] | None:
    return _manifest_from_pattern(pattern) if pattern is not None else None


def production_manifest_is_active(
    pattern: DiscoveredPattern | None,
    *,
    now: datetime | None = None,
) -> bool:
    return bool(production_manifest_status(pattern, now=now)["valid"])


def production_manifest_summary(patterns: list[DiscoveredPattern]) -> dict[str, Any]:
    statuses = [production_manifest_status(pattern) for pattern in patterns]
    valid = [item for item in statuses if item["valid"]]
    blocked = [item for item in statuses if not item["valid"]]
    reason_counts: dict[str, int] = {}
    for item in blocked:
        reason = str(item.get("reason_code") or "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "required": True,
        "gate_required": "DirectorProductionGate",
        "evidence_policy": "canonical_manifest_with_director_production_gate_paper_fill_evidence",
        "eligible_patterns": len(valid),
        "blocked_patterns": len(blocked),
        "blocked_reason_counts": reason_counts,
    }


def _manifest_from_pattern(pattern: DiscoveredPattern) -> dict[str, Any] | None:
    metrics = pattern.metrics_json or {}
    manifest = metrics.get(PRODUCTION_MANIFEST_KEY)
    if isinstance(manifest, dict):
        return manifest
    params = getattr(pattern, "params_json", None) or {}
    manifest = params.get(PRODUCTION_MANIFEST_KEY) if isinstance(params, dict) else None
    return manifest if isinstance(manifest, dict) else None


def _normalized_evidence_packet(
    pattern: DiscoveredPattern | None,
    evidence_packet: dict[str, Any],
) -> dict[str, Any]:
    packet = dict(evidence_packet or {})
    if not str(packet.get("id") or packet.get("packet_id") or "").strip():
        packet["id"] = _default_evidence_packet_id(pattern)
    if not str(packet.get("hash") or packet.get("sha256") or packet.get("packet_hash") or "").strip():
        raw = json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
        packet["hash"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return packet


def _default_manifest_version(pattern: DiscoveredPattern | None, approved_at: datetime) -> str:
    if pattern is None:
        return approved_at.strftime("%Y%m%dT%H%M%SZ")
    pattern_key = str(getattr(pattern, "pattern_key", "") or getattr(pattern, "id", "") or "pattern")
    return f"{pattern_key}:{approved_at.strftime('%Y%m%dT%H%M%SZ')}"


def _default_evidence_packet_id(pattern: DiscoveredPattern | None) -> str:
    if pattern is None:
        return "production-evidence-packet"
    pattern_id = str(getattr(pattern, "id", "") or getattr(pattern, "pattern_key", "") or "pattern")
    return f"production-evidence-pattern-{pattern_id}"


def _canonical_manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key not in _HASH_KEYS}


def _manifest_hash(manifest: dict[str, Any]) -> str:
    for key in ("manifest_hash", "hash", "sha256"):
        value = str(manifest.get(key) or "").strip()
        if value:
            return value
    return ""


def _evidence_packet_errors(manifest: dict[str, Any]) -> list[str]:
    packet = manifest.get("evidence_packet")
    packet_hash = str(
        manifest.get("evidence_packet_hash") or manifest.get("evidence_hash") or ""
    ).strip()
    if isinstance(packet, str):
        if not packet.strip() or not packet_hash:
            return ["missing_evidence_packet"]
        return ["missing_director_production_gate_evidence"]
    if not isinstance(packet, dict) or not packet:
        return ["missing_evidence_packet"]

    errors: list[str] = []
    packet_ref = any(str(packet.get(key) or "").strip() for key in ("id", "packet_id", "uri", "path"))
    packet_hash = packet_hash or next(
        (
            str(packet.get(key) or "").strip()
            for key in ("hash", "sha256", "packet_hash", "evidence_hash")
            if str(packet.get(key) or "").strip()
        ),
        "",
    )
    if not packet_ref:
        errors.append("evidence_packet_ref_missing")
    if not packet_hash:
        errors.append("evidence_packet_hash_missing")

    gate_scope = str(packet.get("gate_scope") or "").strip()
    if gate_scope != PRODUCTION_GATE_SCOPE:
        errors.append("missing_director_production_gate_evidence")
    if packet.get("approved_for_production") is not True:
        errors.append("production_gate_not_approved")
    blockers = packet.get("blockers")
    if not isinstance(blockers, list):
        errors.append("missing_production_gate_blockers")
    elif any(str(blocker).strip() for blocker in blockers):
        errors.append("production_gate_blockers_present")

    if not _paper_fill_thresholds_pass(packet):
        errors.append("paper_fill_evidence_thresholds_missing")
    scientific_contracts = packet.get("scientific_contracts")
    if not isinstance(scientific_contracts, dict) or not scientific_contracts:
        errors.append("scientific_contracts_missing")
    else:
        if scientific_contracts.get("director_gate_passed") is not True:
            errors.append("scientific_contract_director_gate_missing")
        contract_blockers = scientific_contracts.get("blockers")
        if isinstance(contract_blockers, list) and any(str(item).strip() for item in contract_blockers):
            errors.append("scientific_contract_blockers_present")
        contract_packet = scientific_contracts.get("evidence_packet")
        if not isinstance(contract_packet, dict) or not (
            str(contract_packet.get("ref") or "").strip()
            and str(contract_packet.get("hash") or "").strip()
        ):
            errors.append("scientific_contract_evidence_packet_missing")
        provenance = scientific_contracts.get("execution_provenance")
        if not isinstance(provenance, dict) or not (
            provenance.get("costs_reconciled") is True
            and provenance.get("slippage_reconciled") is True
            and provenance.get("fills_reconciled") is True
        ):
            errors.append("scientific_contract_execution_provenance_missing")
    return errors


def _paper_fill_thresholds_pass(packet: dict[str, Any]) -> bool:
    fills = _positive_int(packet.get("ibkr_paper_fills"))
    min_fills = _positive_int(packet.get("min_paper_fills"))
    symbols = _positive_int(packet.get("unique_fill_symbols"))
    min_symbols = _positive_int(packet.get("min_fill_symbols"))
    days = _positive_int(packet.get("unique_fill_days"))
    min_days = _positive_int(packet.get("min_fill_trading_days"))
    if None in {fills, min_fills, symbols, min_symbols, days, min_days}:
        return False
    return bool(
        fills is not None
        and min_fills is not None
        and symbols is not None
        and min_symbols is not None
        and days is not None
        and min_days is not None
        and fills >= min_fills
        and symbols >= min_symbols
        and days >= min_days
    )


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _evidence_packet_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    packet = manifest.get("evidence_packet")
    if not isinstance(packet, dict):
        return {"present": bool(packet)}
    return {
        "id": packet.get("id") or packet.get("packet_id"),
        "uri": packet.get("uri") or packet.get("path"),
        "hash": packet.get("hash") or packet.get("sha256") or packet.get("packet_hash"),
        "gate_scope": packet.get("gate_scope"),
        "approved_for_production": packet.get("approved_for_production"),
        "ibkr_paper_fills": packet.get("ibkr_paper_fills"),
        "min_paper_fills": packet.get("min_paper_fills"),
        "unique_fill_symbols": packet.get("unique_fill_symbols"),
        "min_fill_symbols": packet.get("min_fill_symbols"),
        "unique_fill_days": packet.get("unique_fill_days"),
        "min_fill_trading_days": packet.get("min_fill_trading_days"),
        "scientific_contracts_present": isinstance(packet.get("scientific_contracts"), dict),
    }


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _isoformat(value: datetime | str) -> str:
    parsed = _parse_datetime(value)
    if parsed is not None:
        return parsed.isoformat()
    return str(value)


def _status_value(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _status(valid: bool, reason_code: str, checked_at: datetime, **extra: Any) -> dict[str, Any]:
    return {
        "valid": valid,
        "reason_code": reason_code,
        "checked_at": checked_at.isoformat(),
        **extra,
    }
