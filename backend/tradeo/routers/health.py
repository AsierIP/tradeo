from __future__ import annotations

import json

from fastapi import APIRouter

from tradeo.core.config import get_settings
from tradeo.db.session import SessionLocal
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection
from tradeo.services.watchdog import SystemWatchdog

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "ok": True,
        "app": settings.app_name,
        "mode": settings.trading_mode,
        "live_armed": settings.live_armed,
        "kill_switch_enabled": settings.kill_switch_enabled,
    }


@router.get("/health/notice")
def health_notice() -> dict[str, object]:
    settings = get_settings()
    notice_path = settings.artifacts_path / "web_notice.json"
    if not notice_path.exists():
        return {"visible": False}
    try:
        notice = json.loads(notice_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"visible": False}
    level = notice.get("level")
    message = notice.get("message")
    if level not in {"ok", "error"} or not isinstance(message, str) or not message.strip():
        return {"visible": False}
    return {
        "visible": True,
        "level": level,
        "title": notice.get("title") if isinstance(notice.get("title"), str) else "Tradeo",
        "message": message,
        "updated_at": notice.get("updated_at"),
    }


@router.get("/health/deep")
def deep_health() -> dict[str, object]:
    db = SessionLocal()
    try:
        status = SystemWatchdog().inspect(db)
    finally:
        db.close()
    return {
        **health(),
        "watchdog": status,
    }


@router.get("/health/ibkr")
def ibkr_health() -> dict[str, object]:
    return inspect_ibkr_connection()
