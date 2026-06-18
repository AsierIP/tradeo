from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, DiscoveredPattern, DiscoveredPatternStatus
from tradeo.modules.fox_hunter.production_manifest import (
    production_manifest_status,
    production_manifest_summary,
)
from tradeo.services.runtime_status import worker_runtime_status
from tradeo.services.system_controls import runtime_kill_switch, runtime_kill_switch_active

LIVE_PORTS = {7496, 4001}
RECONCILIATION_ACTIONS = {
    "reconciliation_completed",
    "reconciliation_broker_unreachable",
}


class LiveReadinessError(RuntimeError):
    def __init__(self, status: dict[str, Any]) -> None:
        self.status = status
        reason = str(status.get("primary_block_reason") or "live_readiness_blocked")
        super().__init__(f"live readiness blocked: {reason}")


class LiveReadinessGate:
    """Single fail-closed decision point for live order eligibility."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(
        self,
        db: Session,
        *,
        require_auto_submit: bool = True,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        settings = self.settings
        evaluated_at = _as_utc(now or datetime.now(timezone.utc))
        checks: list[dict[str, Any]] = []

        def add(name: str, ok: bool, reason: str, **details: Any) -> None:
            checks.append({"name": name, "ok": bool(ok), "reason": None if ok else reason, **details})

        runtime_control = runtime_kill_switch(db)
        runtime_kill_enabled = runtime_kill_switch_active(db)
        add("env_kill_switch", not settings.kill_switch_enabled, "kill_switch_enabled")
        add(
            "runtime_kill_switch",
            not runtime_kill_enabled,
            "runtime_kill_switch_enabled",
            control_reason=runtime_control.reason if runtime_control else None,
            updated_at=runtime_control.updated_at.isoformat() if runtime_control else None,
        )
        add("live_armed", settings.live_armed, "live_armed_false")
        if require_auto_submit:
            add(
                "auto_submit_live_orders",
                settings.fox_hunter_auto_submit_live_orders,
                "live_auto_submit_disabled",
            )
        add("trading_mode_live", settings.trading_mode == "live", "trading_mode_not_live")
        add("ibkr_readonly", not settings.ibkr_readonly, "ibkr_readonly")
        add("ibkr_live_port", int(settings.ibkr_port) in LIVE_PORTS, "ibkr_live_port_required")
        add(
            "ibkr_account",
            bool(str(settings.ibkr_account or "").strip()),
            "missing_ibkr_account",
        )
        add(
            "ibkr_allowed_symbols",
            bool(settings.ibkr_allowed_symbol_set),
            "missing_ibkr_allowed_symbols",
            symbol_count=len(settings.ibkr_allowed_symbol_set),
        )

        worker = worker_runtime_status(
            settings,
            max_age_seconds=int(settings.live_readiness_worker_max_age_seconds),
        )
        add(
            "worker_fresh",
            bool(worker.get("ok")),
            str(worker.get("reason") or "worker_not_fresh"),
            status=worker,
        )

        reconciliation = self._reconciliation_status(db, now=evaluated_at)
        add(
            "reconciliation_fresh_clean",
            bool(reconciliation.get("ok")),
            str(reconciliation.get("reason") or "reconciliation_not_ready"),
            status=reconciliation,
        )

        production_patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status == DiscoveredPatternStatus.PRODUCTION)
            .all()
        )
        manifest_statuses = [
            production_manifest_status(pattern, now=evaluated_at) for pattern in production_patterns
        ]
        eligible = [item for item in manifest_statuses if bool(item.get("valid"))]
        manifest_summary = production_manifest_summary(production_patterns)
        add(
            "production_manifest",
            len(eligible) > 0,
            "no_active_production_manifest",
            status=manifest_summary,
        )

        blocked = [check for check in checks if not check["ok"]]
        return {
            "ok": not blocked,
            "allowed": not blocked,
            "state": "allowed" if not blocked else "blocked",
            "orders_allowed": not blocked,
            "primary_block_reason": blocked[0]["reason"] if blocked else None,
            "block_reasons": [str(check["reason"]) for check in blocked],
            "blockers": [
                {"code": str(check["reason"]), "check": str(check["name"])}
                for check in blocked
            ],
            "checks": checks,
            "runtime_kill_switch_enabled": runtime_kill_enabled,
            "runtime_kill_switch_reason": runtime_control.reason if runtime_control else None,
            "worker": worker,
            "reconciliation": reconciliation,
            "eligible_production_manifests": len(eligible),
            "production_status_patterns": len(production_patterns),
            "production_manifest": manifest_summary,
            "ibkr_port": settings.ibkr_port,
            "ibkr_account_configured": bool(str(settings.ibkr_account or "").strip()),
            "ibkr_allowed_symbol_count": len(settings.ibkr_allowed_symbol_set),
            "evaluated_at": evaluated_at.isoformat(),
        }

    def require_ready(self, db: Session, *, require_auto_submit: bool = True) -> dict[str, Any]:
        status = self.evaluate(db, require_auto_submit=require_auto_submit)
        if not status["ok"]:
            raise LiveReadinessError(status)
        return status

    def _reconciliation_status(self, db: Session, *, now: datetime | None = None) -> dict[str, Any]:
        settings = self.settings
        if not settings.reconciliation_enabled:
            return {"ok": False, "reason": "reconciliation_disabled", "last_completed_at": None}
        row = (
            db.query(AuditLog)
            .filter(AuditLog.actor == "reconciliation")
            .filter(AuditLog.action.in_(RECONCILIATION_ACTIONS))
            .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
            .first()
        )
        if row is None:
            return {"ok": False, "reason": "missing_clean_reconciliation", "last_completed_at": None}
        details = row.details_json or {}
        divergence_count = _max_count(details.get("divergence_count"), details.get("divergences"))
        error_count = int(details.get("exit_protection_error_count") or 0)
        warning_count = int(details.get("warning_count") or 0)
        now = _as_utc(now or datetime.now(timezone.utc))
        timestamp = row.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        else:
            timestamp = timestamp.astimezone(timezone.utc)
        age_seconds = (now - timestamp).total_seconds()
        max_age_seconds = int(settings.live_readiness_reconciliation_max_age_seconds)
        latest_unreachable = row.action == "reconciliation_broker_unreachable"
        ok = (
            not latest_unreachable
            and divergence_count == 0
            and error_count == 0
            and warning_count == 0
            and age_seconds <= max_age_seconds
        )
        reason = "ok"
        if latest_unreachable:
            reason = "reconciliation_broker_unreachable"
        elif divergence_count:
            reason = "reconciliation_divergences"
        elif error_count:
            reason = "reconciliation_exit_protection_errors"
        elif warning_count:
            reason = "reconciliation_warnings"
        elif age_seconds > max_age_seconds:
            reason = "stale_reconciliation"
        return {
            "ok": ok,
            "reason": reason,
            "last_action": row.action,
            "last_completed_at": timestamp.isoformat(),
            "age_seconds": round(age_seconds, 1),
            "max_age_seconds": max_age_seconds,
            "divergence_count": divergence_count,
            "warning_count": warning_count,
            "exit_protection_error_count": error_count,
        }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _max_count(value: Any, rows: Any) -> int:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        count = 0
    if isinstance(rows, list):
        count = max(count, len(rows))
    return count
