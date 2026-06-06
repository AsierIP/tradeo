from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.core.security import require_admin
from tradeo.db.models import AuditLog
from tradeo.db.session import get_db
from tradeo.schemas import KillSwitchRequest

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/kill-switch")
def set_kill_switch(
    request: KillSwitchRequest,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    settings = get_settings()
    # Runtime env values are immutable in Settings cache. This endpoint logs intent for
    # audit and returns clear instructions; Docker env must be changed and restarted.
    db.add(
        AuditLog(
            actor="human",
            action="kill_switch_requested",
            entity_type="risk",
            details_json=request.model_dump(),
        )
    )
    db.commit()
    return {
        "requested": request.enabled,
        "current_env_value": settings.kill_switch_enabled,
        "message": "Set TRADEO_KILL_SWITCH_ENABLED in .env and restart containers to make it persistent.",
    }
