from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from tradeo.core.config import Settings, get_settings

WORKER_HEARTBEAT = "worker_heartbeat.json"
ENTRY_SCAN_STATUS = "entry_scan_status.json"


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
    path.write_text(json.dumps(payload), encoding="utf-8")


def worker_runtime_status(settings: Settings | None = None, *, max_age_seconds: int = 90) -> dict[str, Any]:
    settings = settings or get_settings()
    path = settings.artifacts_path / WORKER_HEARTBEAT
    if not path.exists():
        return {"ok": False, "state": "stopped", "age_seconds": None, "reason": "missing_worker_heartbeat"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamp = datetime.fromisoformat(str(payload["timestamp"]))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return {"ok": False, "state": "stopped", "age_seconds": None, "reason": "invalid_worker_heartbeat"}
    age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
    ok = age_seconds <= max_age_seconds and bool(payload.get("scheduler_enabled"))
    return {
        "ok": ok,
        "state": "ok" if ok else "stopped",
        "age_seconds": round(age_seconds, 1),
        "reason": "ok" if ok else "stale_or_scheduler_disabled",
    }


def write_entry_scan_status(module: str, result: dict[str, Any], settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    path = settings.artifacts_path / ENTRY_SCAN_STATUS
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    previous = payload.get(module) or {}
    last_symbols_checked = int(result.get("symbols_checked") or 0)
    cumulative_symbols_checked = int(previous.get("cumulative_symbols_checked") or 0) + last_symbols_checked
    payload[module] = {
        "symbols_checked": cumulative_symbols_checked,
        "last_symbols_checked": last_symbols_checked,
        "cumulative_symbols_checked": cumulative_symbols_checked,
        "patterns_checked": int(result.get("patterns_checked") or 0),
        "matches_found": int(result.get("matches_found") or 0),
        "skipped_reason": result.get("skipped_reason"),
        "market_session": result.get("market_session"),
        "generated_at": result.get("generated_at") or datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


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
        "symbols_checked": int(data.get("cumulative_symbols_checked") or data.get("symbols_checked") or 0),
        "last_symbols_checked": int(data.get("last_symbols_checked") or data.get("symbols_checked") or 0),
        "patterns_checked": int(data.get("patterns_checked") or 0),
        "matches_found": int(data.get("matches_found") or 0),
        "skipped_reason": data.get("skipped_reason"),
        "market_session": data.get("market_session"),
        "generated_at": data.get("generated_at"),
    }
