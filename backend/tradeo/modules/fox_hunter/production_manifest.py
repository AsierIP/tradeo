from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus

PRODUCTION_MANIFEST_KEY = "production_manifest"
PRODUCTION_MANIFEST_SCHEMA = "tradeo.production_manifest.v1"
PRODUCTION_MANIFEST_HASH_ALGORITHM = "sha256_canonical_v1"
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
    manifest_status = str(manifest.get("status") or "").lower()
    approved = bool(manifest.get("approved")) or manifest_status == "approved"
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
    if not _manifest_hash(manifest):
        errors.append("missing_manifest_hash")
    if not _evidence_packet_ok(manifest):
        errors.append("missing_evidence_packet")
    if (
        str(manifest.get("hash_algorithm") or "") == PRODUCTION_MANIFEST_HASH_ALGORITHM
        and _manifest_hash(manifest)
        and production_manifest_hash(manifest) != _manifest_hash(manifest)
    ):
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
        manifest_hash=_manifest_hash(manifest),
        evidence_packet=_evidence_packet_summary(manifest),
        hash_verified=valid and str(manifest.get("hash_algorithm") or "") == PRODUCTION_MANIFEST_HASH_ALGORITHM,
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


def _evidence_packet_ok(manifest: dict[str, Any]) -> bool:
    packet = manifest.get("evidence_packet")
    packet_hash = str(
        manifest.get("evidence_packet_hash") or manifest.get("evidence_hash") or ""
    ).strip()
    if isinstance(packet, dict):
        packet_ref = any(str(packet.get(key) or "").strip() for key in ("id", "packet_id", "uri", "path"))
        packet_hash = packet_hash or next(
            (
                str(packet.get(key) or "").strip()
                for key in ("hash", "sha256", "packet_hash", "evidence_hash")
                if str(packet.get(key) or "").strip()
            ),
            "",
        )
        return packet_ref and bool(packet_hash)
    if isinstance(packet, str):
        return bool(packet.strip() and packet_hash)
    return False


def _evidence_packet_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    packet = manifest.get("evidence_packet")
    if not isinstance(packet, dict):
        return {"present": bool(packet)}
    return {
        "id": packet.get("id") or packet.get("packet_id"),
        "uri": packet.get("uri") or packet.get("path"),
        "hash": packet.get("hash") or packet.get("sha256") or packet.get("packet_hash"),
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
