#!/usr/bin/env python3
"""Check for new Tradeo pattern audit events.

This cron payload reads only ``audit_logs.action='new_pattern_discovered'``.
It never queries ``discovered_patterns``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT_DIR / "memory" / "pattern-alert-audit-state.json"
DB_USER = os.environ.get("TRADEO_NOTIFY_DB_USER", "tradeo")
DB_NAME = os.environ.get("TRADEO_NOTIFY_DB_NAME", "tradeo")
MESSAGE_ACCOUNT_ID = "tradeo"
MESSAGE_CHANNEL = "telegram"
MESSAGE_CHAT_ID = "telegram:1600299362"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def short_error(exc: BaseException) -> str:
    return " ".join((str(exc).strip() or exc.__class__.__name__).split())[:300]


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def report(
    *,
    initialized: bool,
    state_updated: bool,
    last_seen_audit_id: int | None,
    events: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "initialized": initialized,
        "state_updated": state_updated,
        "last_seen_audit_id": last_seen_audit_id,
        "events": [
            {"id": int(event["id"]), "message": event["message"]}
            for event in events or []
        ],
        "error": error,
    }


def psql(sql: str) -> str:
    proc = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", DB_USER, "-d", DB_NAME, "-Atc", sql],
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "psql failed")
    return proc.stdout.strip()


def telegram_target(chat_id: str) -> str:
    return chat_id.removeprefix("telegram:")


def send_visible_telegram_message(message: str) -> None:
    proc = subprocess.run(
        [
            "openclaw",
            "message",
            "send",
            "--account",
            MESSAGE_ACCOUNT_ID,
            "--channel",
            MESSAGE_CHANNEL,
            "--target",
            telegram_target(MESSAGE_CHAT_ID),
            "--message",
            message,
            "--json",
        ],
        cwd=ROOT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "openclaw message send failed")


def load_state() -> tuple[dict[str, Any] | None, str | None]:
    if not STATE_FILE.exists():
        return None, None
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"state read error: {short_error(exc)}"
    if not isinstance(state, dict):
        return None, "state read error: expected JSON object"
    return state, None


def write_state(state: dict[str, Any]) -> str | None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(STATE_FILE)
    except Exception as exc:  # noqa: BLE001
        return f"state write error: {short_error(exc)}"
    return None


def add_error_note(kind: str, error: str) -> str | None:
    timestamp = now_iso()
    state, _ = load_state()
    state = state if isinstance(state, dict) else {}
    notes = state.get("notes")
    if not isinstance(notes, list):
        notes = []
    notes.append(f"{timestamp} {kind}: {short_error(Exception(error))}")
    state["notes"] = notes[-20:]
    state["last_error_note"] = {"timestamp": timestamp, "kind": kind, "error": short_error(Exception(error))}
    state["last_check_at"] = timestamp
    state["last_checked_at"] = timestamp
    state["updated_at"] = timestamp
    return write_state(state)


def append_error_note(state: dict[str, Any], kind: str, error: str) -> None:
    timestamp = now_iso()
    notes = state.get("notes")
    if not isinstance(notes, list):
        notes = []
    notes.append(f"{timestamp} {kind}: {short_error(Exception(error))}")
    state["notes"] = notes[-20:]
    state["last_error_note"] = {"timestamp": timestamp, "kind": kind, "error": short_error(Exception(error))}


def clear_error_note(state: dict[str, Any]) -> None:
    state.pop("last_error_note", None)


def max_audit_id() -> int:
    raw = psql("SELECT COALESCE(MAX(id), 0) FROM audit_logs WHERE action='new_pattern_discovered';")
    return int(raw or "0")


def fetch_events(last_seen_id: int) -> list[dict[str, Any]]:
    sql = f"""
SELECT json_build_object(
  'id', id,
  'timestamp', timestamp,
  'entity_id', entity_id,
  'details_json', details_json
)::text
FROM audit_logs
WHERE id > {int(last_seen_id)}
  AND action = 'new_pattern_discovered'
ORDER BY id ASC;
"""
    raw = psql(sql)
    if not raw:
        return []
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def lane_from(details: dict[str, Any]) -> Any:
    lane = details.get("lane")
    if lane:
        return lane
    timeframe = str(details.get("timeframe") or "").strip().lower()
    if timeframe in {"1m", "2m", "3m", "5m", "10m", "15m", "30m", "60m"}:
        return "intraday"
    if timeframe:
        return "daily"
    return None


def pick(details: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = details.get(key)
        if value is not None:
            return value
    return None


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    details = event.get("details_json") or {}
    if not isinstance(details, dict):
        details = {}
    quality = details.get("quality") or {}
    if not isinstance(quality, dict):
        quality = {}
    normalized = {
        "id": int(event["id"]),
        "lane": lane_from(details),
        "timeframe": details.get("timeframe"),
        "side": details.get("side"),
        "name": pick(details, "name", "pattern_name", "pattern_key") or f"pattern {details.get('pattern_id') or event.get('entity_id') or event.get('id')}",
        "status": pick(details, "status", "pattern_status"),
        "quality_label": quality.get("label") or details.get("quality_label"),
        "quality_summary": quality.get("summary") or details.get("quality_summary"),
        "score": details.get("score"),
        "expectancy_r": details.get("expectancy_r"),
        "profit_factor": details.get("profit_factor"),
        "reward_risk_estimate": details.get("reward_risk_estimate"),
        "sample_count": details.get("sample_count"),
        "symbol_count": details.get("symbol_count"),
    }
    normalized["message"] = format_spanish_message(normalized)
    return normalized


def label_or_unknown(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text or "desconocido"


def metric(value: Any) -> str:
    if value is None:
        return "n/d"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def format_spanish_message(event: dict[str, Any]) -> str:
    lane = {"daily": "Daily", "intraday": "Intradía"}.get(str(event.get("lane") or ""), "Desconocido")
    side = {"long": "largo", "short": "corto"}.get(str(event.get("side") or "").lower(), label_or_unknown(event.get("side")))
    quality = label_or_unknown(event.get("quality_label"))
    if event.get("quality_summary"):
        quality = f"{quality}: {event['quality_summary']}"
    metric_parts = [
        f"score {metric(event.get('score'))}",
        f"expectancy R {metric(event.get('expectancy_r'))}",
        f"profit factor {metric(event.get('profit_factor'))}",
        f"reward/risk {metric(event.get('reward_risk_estimate'))}",
    ]
    if event.get("sample_count") is not None:
        metric_parts.append(f"muestras {metric(event.get('sample_count'))}")
    if event.get("symbol_count") is not None:
        metric_parts.append(f"símbolos {metric(event.get('symbol_count'))}")
    return "\n".join(
        [
            "Tradeo: patrón nuevo.",
            f"{lane} · {label_or_unknown(event.get('timeframe'))} · {side}",
            f"{label_or_unknown(event.get('name'))} · estado {label_or_unknown(event.get('status'))}",
            f"Calidad: {quality}",
            "Métricas: " + ", ".join(metric_parts),
            f"AuditLog #{event['id']}",
        ]
    )


def initialize_state(current_max: int) -> str | None:
    timestamp = now_iso()
    return write_state(
        {
            "last_seen_audit_id": current_max,
            "updated_at": timestamp,
            "last_check_at": timestamp,
            "last_checked_at": timestamp,
            "last_event_count": 0,
            "last_check": {"timestamp": timestamp, "initialized": True, "events_found": 0, "db_ok": True},
            "last_run_result": {"new_events": 0, "new_last_seen": current_max},
            "last_payloads": [],
            "last_result": "initialized from current max new_pattern_discovered audit id; no notice sent",
        }
    )


def main() -> int:
    state, state_error = load_state()
    if state_error:
        write_error = add_error_note("state", state_error)
        emit(
            report(
                initialized=False,
                state_updated=write_error is None,
                last_seen_audit_id=None,
                error="; ".join(item for item in (state_error, write_error) if item),
            )
        )
        return 1

    try:
        previous_last_seen = None if state is None else state.get("last_seen_audit_id")
        if previous_last_seen is not None:
            previous_last_seen = int(previous_last_seen)
    except Exception as exc:  # noqa: BLE001
        error = f"state parse error: {short_error(exc)}"
        write_error = add_error_note("state", error)
        emit(
            report(
                initialized=False,
                state_updated=write_error is None,
                last_seen_audit_id=None,
                error="; ".join(item for item in (error, write_error) if item),
            )
        )
        return 1

    if state is None or previous_last_seen is None:
        try:
            current_max = max_audit_id()
        except Exception as exc:  # noqa: BLE001
            db_error = f"DB error: {short_error(exc)}"
            write_error = add_error_note("db", db_error)
            emit(
                report(
                    initialized=False,
                    state_updated=write_error is None,
                    last_seen_audit_id=None,
                    error="; ".join(item for item in (db_error, write_error) if item),
                )
            )
            return 1
        write_error = initialize_state(current_max)
        emit(
            report(
                initialized=True,
                state_updated=write_error is None,
                last_seen_audit_id=current_max,
                error=write_error,
            )
        )
        return 1 if write_error else 0

    try:
        rows = fetch_events(previous_last_seen)
    except Exception as exc:  # noqa: BLE001
        db_error = f"DB error: {short_error(exc)}"
        write_error = add_error_note("db", db_error)
        emit(
            report(
                initialized=False,
                state_updated=write_error is None,
                last_seen_audit_id=previous_last_seen,
                error="; ".join(item for item in (db_error, write_error) if item),
            )
        )
        return 1

    events = [normalize_event(row) for row in rows]
    timestamp = now_iso()
    clear_error_note(state)
    state.update(
        {
            "last_seen_audit_id": previous_last_seen,
            "updated_at": timestamp,
            "last_check_at": timestamp,
            "last_checked_at": timestamp,
            "last_event_count": len(events),
            "last_check": {"timestamp": timestamp, "initialized": False, "events_found": len(events), "db_ok": True},
            "last_run_result": {"new_events": len(events), "new_last_seen": previous_last_seen},
            "last_payloads": [{"id": event["id"], "message": event["message"]} for event in events],
            "last_result": (
                f"found {len(events)} new_pattern_discovered audit log events"
                if events
                else "no new new_pattern_discovered audit log events"
            ),
        }
    )

    sent_events: list[dict[str, Any]] = []
    for event in events:
        try:
            send_visible_telegram_message(event["message"])
        except Exception as exc:  # noqa: BLE001
            msg_error = f"messaging error for audit_log {event['id']}: {short_error(exc)}"
            append_error_note(state, "messaging", msg_error)
            state["updated_at"] = now_iso()
            state["last_result"] = msg_error
            state["last_run_result"] = {"new_events": len(events), "sent_events": len(sent_events), "new_last_seen": state["last_seen_audit_id"]}
            write_error = write_state(state)
            emit(
                report(
                    initialized=False,
                    state_updated=write_error is None,
                    last_seen_audit_id=int(state["last_seen_audit_id"]),
                    events=sent_events,
                    error="; ".join(item for item in (msg_error, write_error) if item),
                )
            )
            return 1

        sent_events.append(event)
        state["last_seen_audit_id"] = int(event["id"])
        state["updated_at"] = now_iso()
        state["last_run_result"] = {"new_events": len(events), "sent_events": len(sent_events), "new_last_seen": int(event["id"])}
        write_error = write_state(state)
        if write_error:
            emit(
                report(
                    initialized=False,
                    state_updated=False,
                    last_seen_audit_id=int(event["id"]),
                    events=sent_events,
                    error=write_error,
                )
            )
            return 1

    new_last_seen = int(state["last_seen_audit_id"])
    write_error = write_state(state)
    emit(
        report(
            initialized=False,
            state_updated=write_error is None,
            last_seen_audit_id=new_last_seen,
            events=sent_events,
            error=write_error,
        )
    )
    return 1 if write_error else 0


if __name__ == "__main__":
    sys.exit(main())
