from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradeo.core.config import Settings, get_settings

WORKER_HEARTBEAT = "worker_heartbeat.json"
ENTRY_SCAN_STATUS = "entry_scan_status.json"
INTRADAY_SESSION_STATUS = "intraday_session_status.json"
ZERO_ORDER_ALERT_STREAK = 3


def write_worker_heartbeat(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    path = settings.artifacts_path / WORKER_HEARTBEAT
    payload = {
        "pid": os.getpid(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scheduler_enabled": settings.scheduler_enabled,
        "laboratory_scanner_enabled": settings.laboratory_scanner_enabled,
        "fox_hunter_enabled": settings.fox_hunter_enabled,
    }
    _write_json_atomic(path, payload)


def worker_runtime_status(
    settings: Settings | None = None, *, max_age_seconds: int = 90, now: datetime | None = None
) -> dict[str, Any]:
    settings = settings or get_settings()
    path = settings.artifacts_path / WORKER_HEARTBEAT
    if not path.exists():
        return {
            "ok": False,
            "state": "stopped",
            "age_seconds": None,
            "timestamp": None,
            "reason": "missing_worker_heartbeat",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamp = _as_utc(datetime.fromisoformat(str(payload["timestamp"])))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return {
            "ok": False,
            "state": "stopped",
            "age_seconds": None,
            "timestamp": None,
            "reason": "invalid_worker_heartbeat",
        }
    age_seconds = (_as_utc(now or datetime.now(timezone.utc)) - timestamp).total_seconds()
    ok = age_seconds <= max_age_seconds and bool(payload.get("scheduler_enabled"))
    return {
        "ok": ok,
        "state": "ok" if ok else "stopped",
        "age_seconds": round(age_seconds, 1),
        "timestamp": timestamp.isoformat(),
        "reason": "ok" if ok else "stale_or_scheduler_disabled",
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def write_entry_scan_status(
    module: str, result: dict[str, Any], settings: Settings | None = None
) -> None:
    settings = settings or get_settings()
    path = settings.artifacts_path / ENTRY_SCAN_STATUS
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    previous = payload.get(module) or {}
    last_symbols_checked = int(result.get("symbols_checked") or 0)
    cumulative_symbols_checked = (
        int(previous.get("cumulative_symbols_checked") or 0) + last_symbols_checked
    )
    matches_found = int(result.get("matches_found") or 0)
    orders_submitted = int(result.get("orders_submitted") or 0)
    scan_duration_ms = _optional_float(result.get("scan_duration_ms"))
    rates = _scan_rates(
        duration_ms=scan_duration_ms,
        symbols=last_symbols_checked,
        patterns=int(result.get("patterns_checked") or 0),
        matches=matches_found,
        signals=int(result.get("signals_created") or 0),
        orders=orders_submitted,
        candidates=int(result.get("entry_variants_considered") or matches_found),
    )
    funnel = _entry_scan_funnel(result)
    execute_orders = bool(result.get("execute_orders", True))
    skipped_reason = result.get("skipped_reason")
    zero_order_scan = (
        execute_orders and matches_found > 0 and orders_submitted == 0 and not skipped_reason
    )
    zero_order_scan_streak = (
        int(previous.get("zero_order_scan_streak") or 0) + 1 if zero_order_scan else 0
    )
    payload[module] = {
        "symbols_checked": cumulative_symbols_checked,
        "last_symbols_checked": last_symbols_checked,
        "cumulative_symbols_checked": cumulative_symbols_checked,
        "patterns_checked": int(result.get("patterns_checked") or 0),
        "matches_found": matches_found,
        "entry_variants_considered": int(result.get("entry_variants_considered") or 0),
        "scan_duration_ms": scan_duration_ms,
        "scan_rates_per_minute": rates,
        "funnel": funnel,
        "execute_orders": execute_orders,
        "signals_created": int(result.get("signals_created") or 0),
        "orders_submitted": orders_submitted,
        "skipped_duplicates": int(result.get("skipped_duplicates") or 0),
        "skipped_cooldown": int(result.get("skipped_cooldown") or 0),
        "rejected_by_entry_gate": int(result.get("rejected_by_entry_gate") or 0),
        "rejected_by_entry_quality": int(result.get("rejected_by_entry_quality") or 0),
        "rejected_by_ambiguity": int(result.get("rejected_by_ambiguity") or 0),
        "rejected_by_risk": int(result.get("rejected_by_risk") or 0),
        "rejected_by_production_manifest": int(result.get("rejected_by_production_manifest") or 0),
        "production_manifest_rejection_reason_counts": dict(
            result.get("production_manifest_rejection_reason_counts") or {}
        ),
        "near_miss_shadow_observations_opened": int(
            result.get("near_miss_shadow_observations_opened") or 0
        ),
        "shadow_no_order_observations_opened": int(
            result.get("shadow_no_order_observations_opened") or 0
        ),
        "paper_observations_opened": int(result.get("paper_observations_opened") or 0),
        "paper_observations_closed": int(result.get("paper_observations_closed") or 0),
        "order_errors": list(result.get("order_errors") or []),
        "order_skip_reason_counts": dict(result.get("order_skip_reason_counts") or {}),
        "zero_order_scan_streak": zero_order_scan_streak,
        "zero_order_alert": zero_order_scan_streak >= ZERO_ORDER_ALERT_STREAK,
        "zero_order_block_reason": _entry_scan_zero_order_reason(result)
        if zero_order_scan
        else None,
        "skipped_reason": skipped_reason,
        "market_session": result.get("market_session"),
        "generated_at": result.get("generated_at") or datetime.now(timezone.utc).isoformat(),
    }
    _write_json_atomic(path, payload)


def entry_scan_status(module: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    path = settings.artifacts_path / ENTRY_SCAN_STATUS
    if not path.exists():
        return {
            "symbols_checked": 0,
            "last_symbols_checked": 0,
            "patterns_checked": 0,
            "matches_found": 0,
            "generated_at": None,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "symbols_checked": 0,
            "last_symbols_checked": 0,
            "patterns_checked": 0,
            "matches_found": 0,
            "generated_at": None,
        }
    data = payload.get(module) or {}
    return {
        "symbols_checked": int(
            data.get("cumulative_symbols_checked") or data.get("symbols_checked") or 0
        ),
        "last_symbols_checked": int(
            data.get("last_symbols_checked") or data.get("symbols_checked") or 0
        ),
        "patterns_checked": int(data.get("patterns_checked") or 0),
        "matches_found": int(data.get("matches_found") or 0),
        "entry_variants_considered": int(data.get("entry_variants_considered") or 0),
        "scan_duration_ms": _optional_float(data.get("scan_duration_ms")),
        "scan_rates_per_minute": dict(data.get("scan_rates_per_minute") or {}),
        "funnel": dict(data.get("funnel") or {}),
        "execute_orders": bool(data.get("execute_orders", True)),
        "signals_created": int(data.get("signals_created") or 0),
        "orders_submitted": int(data.get("orders_submitted") or 0),
        "skipped_duplicates": int(data.get("skipped_duplicates") or 0),
        "skipped_cooldown": int(data.get("skipped_cooldown") or 0),
        "rejected_by_entry_gate": int(data.get("rejected_by_entry_gate") or 0),
        "rejected_by_entry_quality": int(data.get("rejected_by_entry_quality") or 0),
        "rejected_by_ambiguity": int(data.get("rejected_by_ambiguity") or 0),
        "rejected_by_risk": int(data.get("rejected_by_risk") or 0),
        "rejected_by_production_manifest": int(data.get("rejected_by_production_manifest") or 0),
        "production_manifest_rejection_reason_counts": dict(
            data.get("production_manifest_rejection_reason_counts") or {}
        ),
        "near_miss_shadow_observations_opened": int(
            data.get("near_miss_shadow_observations_opened") or 0
        ),
        "shadow_no_order_observations_opened": int(
            data.get("shadow_no_order_observations_opened") or 0
        ),
        "paper_observations_opened": int(data.get("paper_observations_opened") or 0),
        "paper_observations_closed": int(data.get("paper_observations_closed") or 0),
        "order_errors": list(data.get("order_errors") or []),
        "order_skip_reason_counts": dict(data.get("order_skip_reason_counts") or {}),
        "zero_order_scan_streak": int(data.get("zero_order_scan_streak") or 0),
        "zero_order_alert": bool(data.get("zero_order_alert")),
        "zero_order_block_reason": data.get("zero_order_block_reason"),
        "skipped_reason": data.get("skipped_reason"),
        "market_session": data.get("market_session"),
        "generated_at": data.get("generated_at"),
    }


def write_intraday_session_status(
    job_id: str,
    result: dict[str, Any],
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    path = settings.artifacts_path / INTRADAY_SESSION_STATUS
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    jobs = dict(payload.get("jobs") or {})
    generated_at = result.get("generated_at") or datetime.now(timezone.utc).isoformat()
    jobs[job_id] = {
        "job_id": job_id,
        "status": str(result.get("status") or "noop"),
        "reason": result.get("reason"),
        "generated_at": generated_at,
        "details": dict(result.get("details") or {}),
    }
    payload = {
        "intraday_enabled": settings.intraday_enabled,
        "paper_enabled": settings.intraday_paper_enabled,
        "live_enabled": settings.intraday_live_enabled,
        "live_armed": settings.intraday_live_armed,
        "updated_at": generated_at,
        "jobs": jobs,
    }
    _write_json_atomic(path, payload)


def intraday_session_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    path = settings.artifacts_path / INTRADAY_SESSION_STATUS
    if not path.exists():
        return {
            "intraday_enabled": settings.intraday_enabled,
            "paper_enabled": settings.intraday_paper_enabled,
            "live_enabled": settings.intraday_live_enabled,
            "live_armed": settings.intraday_live_armed,
            "updated_at": None,
            "jobs": {},
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "intraday_enabled": settings.intraday_enabled,
            "paper_enabled": settings.intraday_paper_enabled,
            "live_enabled": settings.intraday_live_enabled,
            "live_armed": settings.intraday_live_armed,
            "updated_at": None,
            "jobs": {},
            "reason": "invalid_intraday_session_status",
        }
    return {
        "intraday_enabled": bool(payload.get("intraday_enabled")),
        "paper_enabled": bool(payload.get("paper_enabled")),
        "live_enabled": bool(payload.get("live_enabled")),
        "live_armed": bool(payload.get("live_armed")),
        "updated_at": payload.get("updated_at"),
        "jobs": dict(payload.get("jobs") or {}),
    }


def _entry_scan_zero_order_reason(result: dict[str, Any]) -> str:
    order_errors = list(result.get("order_errors") or [])
    if order_errors:
        reason = order_errors[0].get("reason_code") if isinstance(order_errors[0], dict) else None
        return str(reason or "order_errors")
    explicit_reasons = result.get("order_skip_reason_counts") or {}
    if isinstance(explicit_reasons, dict) and explicit_reasons:
        dominant_reason = max(explicit_reasons.items(), key=lambda item: int(item[1] or 0))[0]
        return str(dominant_reason or "order_skip")
    counters = [
        ("rejected_by_entry_gate", "entry_gate"),
        ("rejected_by_risk", "risk"),
        ("rejected_by_entry_quality", "entry_quality"),
        ("skipped_duplicates", "duplicates"),
        ("skipped_cooldown", "cooldown"),
    ]
    dominant = max(counters, key=lambda item: int(result.get(item[0]) or 0))
    if int(result.get(dominant[0]) or 0) > 0:
        return dominant[1]
    if int(result.get("signals_created") or 0) > 0:
        return "signals_created_without_orders"
    return "unknown"


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return round(number, 3)


def _scan_rates(
    *,
    duration_ms: float | None,
    symbols: int,
    patterns: int,
    matches: int,
    signals: int,
    orders: int,
    candidates: int,
) -> dict[str, float]:
    if duration_ms is None or duration_ms <= 0:
        return {}
    minutes = max(duration_ms / 60000.0, 1e-9)
    return {
        "symbols_per_min": round(symbols / minutes, 3),
        "patterns_per_min": round(patterns / minutes, 3),
        "candidates_per_min": round(candidates / minutes, 3),
        "matches_per_min": round(matches / minutes, 3),
        "signals_per_min": round(signals / minutes, 3),
        "orders_per_min": round(orders / minutes, 3),
    }


def _entry_scan_funnel(result: dict[str, Any]) -> dict[str, int]:
    keys = (
        "symbols_checked",
        "patterns_checked",
        "entry_variants_considered",
        "matches_found",
        "signals_created",
        "orders_submitted",
        "skipped_duplicates",
        "skipped_cooldown",
        "rejected_by_entry_gate",
        "rejected_by_entry_quality",
        "rejected_by_ambiguity",
        "rejected_by_risk",
        "rejected_by_production_manifest",
        "near_miss_shadow_observations_opened",
        "shadow_no_order_observations_opened",
        "paper_observations_opened",
        "paper_observations_closed",
    )
    return {key: int(result.get(key) or 0) for key in keys}


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload))
        os.replace(tmp_name, path)
        try:
            os.chmod(path, 0o644)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
