from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.db.models import AuditLog


def add_internal_alert(
    db: Session,
    *,
    source: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
    entity_type: str = "system",
    entity_id: str = "",
) -> AuditLog | None:
    """Add an internal ops alert to the current transaction.

    This intentionally stays local: no webhooks, vendors, email or live-trading
    side effects. Operators can poll ``audit_logs`` for
    ``action='internal_ops_alert'``.
    """
    if not get_settings().ops_alerting_enabled:
        return None
    alert = AuditLog(
        actor="ops_alerting",
        action="internal_ops_alert",
        entity_type=entity_type,
        entity_id=entity_id,
        details_json={
            "schema_version": 1,
            "source": source,
            "severity": severity,
            "message": message,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(details or {}),
        },
    )
    db.add(alert)
    return alert


def record_internal_alert(
    db: Session,
    *,
    source: str,
    severity: str,
    message: str,
    details: dict[str, Any] | None = None,
    entity_type: str = "system",
    entity_id: str = "",
    rollback_first: bool = False,
) -> bool:
    """Persist one alert best-effort and never mask the original failure."""
    try:
        if rollback_first:
            db.rollback()
        alert = add_internal_alert(
            db,
            source=source,
            severity=severity,
            message=message,
            details=details,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if alert is None:
            return False
        db.commit()
        return True
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("failed to persist internal ops alert: {}", exc)
        return False


def record_job_failure(db: Session, *, job_id: str, exc: BaseException) -> bool:
    return record_internal_alert(
        db,
        source="scheduler",
        severity="critical",
        message=f"scheduler job failed: {job_id}",
        details={
            "job_id": job_id,
            "exception_type": exc.__class__.__name__,
            "error": str(exc),
        },
        entity_type="scheduler_job",
        entity_id=job_id,
        rollback_first=True,
    )
