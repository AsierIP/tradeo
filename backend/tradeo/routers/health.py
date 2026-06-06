from __future__ import annotations

from fastapi import APIRouter

from tradeo.core.config import get_settings

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
