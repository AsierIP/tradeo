"""Runtime kill switch persisted in the database (informe §4.5).

TRADEO_KILL_SWITCH_ENABLED is read once at startup, so an automatic safety
trigger could never make it bite without a container restart. This module adds
a DB-persisted runtime kill switch that every order path checks in addition to
the env flag. Activation is idempotent and always audited.

The env flag remains the manual, restart-surviving master switch; the runtime
switch is the automatic one (reconciliation divergence, future triggers).
Either being active blocks order submission.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from tradeo.db.models import AuditLog, SystemControl

KILL_SWITCH_KEY = "kill_switch"

__all__ = [
    "KILL_SWITCH_KEY",
    "runtime_kill_switch",
    "runtime_kill_switch_active",
    "activate_runtime_kill_switch",
    "deactivate_runtime_kill_switch",
]


def runtime_kill_switch(db: Session) -> SystemControl | None:
    return db.query(SystemControl).filter(SystemControl.key == KILL_SWITCH_KEY).first()


def runtime_kill_switch_active(db: Session) -> bool:
    control = runtime_kill_switch(db)
    return bool(control is not None and control.enabled)


def activate_runtime_kill_switch(
    db: Session,
    *,
    reason: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> SystemControl:
    """Persist the runtime kill switch as active. Idempotent, always audited."""
    control = runtime_kill_switch(db)
    already_active = bool(control is not None and control.enabled)
    if control is None:
        control = SystemControl(key=KILL_SWITCH_KEY)
        db.add(control)
    control.enabled = True
    control.reason = reason
    control.actor = actor
    control.details_json = details or {}
    control.updated_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            actor=actor,
            action="runtime_kill_switch_activated",
            entity_type="system_control",
            entity_id=KILL_SWITCH_KEY,
            details_json={
                "reason": reason,
                "already_active": already_active,
                **(details or {}),
            },
        )
    )
    db.commit()
    return control


def deactivate_runtime_kill_switch(
    db: Session,
    *,
    reason: str,
    actor: str,
) -> SystemControl | None:
    """Deactivate the runtime kill switch. Meant for explicit human action."""
    control = runtime_kill_switch(db)
    if control is None or not control.enabled:
        return control
    control.enabled = False
    control.reason = reason
    control.actor = actor
    control.updated_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            actor=actor,
            action="runtime_kill_switch_deactivated",
            entity_type="system_control",
            entity_id=KILL_SWITCH_KEY,
            details_json={"reason": reason},
        )
    )
    db.commit()
    return control
