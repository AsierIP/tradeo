from __future__ import annotations

from fastapi import APIRouter

from tradeo.core.config import get_settings
from tradeo.db.session import SessionLocal
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
