from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.db.models import AuditLog, DiscoveredPatternMatch, DiscoveryRun


class SystemWatchdog:
    """Cheap deterministic health checks and local recovery.

    This deliberately avoids LLM calls. It only inspects local DB state and fixes
    scheduler blockers that are safe to repair from inside the app.
    """

    actor = "system_watchdog"

    def inspect(self, db: Session) -> dict[str, Any]:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(minutes=settings.watchdog_stale_discovery_minutes)
        running_runs = (
            db.query(DiscoveryRun)
            .filter(DiscoveryRun.status == "running")
            .order_by(DiscoveryRun.started_at.asc())
            .all()
        )
        stale_runs = [run for run in running_runs if self._as_utc(run.started_at) < stale_cutoff]
        latest_run = db.query(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).first()
        latest_match_at = db.query(func.max(DiscoveredPatternMatch.matched_at)).scalar()
        return {
            "ok": not stale_runs,
            "watchdog_enabled": settings.watchdog_enabled,
            "running_discovery_runs": [
                {
                    "id": run.id,
                    "started_at": run.started_at.isoformat(),
                    "age_seconds": round((now - self._as_utc(run.started_at)).total_seconds(), 1),
                }
                for run in running_runs
            ],
            "stale_discovery_runs": [run.id for run in stale_runs],
            "latest_discovery_run": self._run_summary(latest_run),
            "latest_pattern_match_at": latest_match_at.isoformat() if latest_match_at else None,
        }

    def repair(self, db: Session) -> dict[str, Any]:
        settings = get_settings()
        status = self.inspect(db)
        repaired: list[dict[str, Any]] = []
        if not settings.watchdog_enabled:
            return {**status, "repaired": repaired}
        if settings.watchdog_close_stale_discovery_runs:
            for run_id in status["stale_discovery_runs"]:
                run = db.get(DiscoveryRun, run_id)
                if run is None or run.status != "running":
                    continue
                now = datetime.now(timezone.utc)
                run.status = "failed"
                run.finished_at = now
                run.duration_seconds = round((now - self._as_utc(run.started_at)).total_seconds(), 3)
                run.summary_json = {
                    **(run.summary_json or {}),
                    "error": "stale running discovery closed by system watchdog",
                    "closed_by": self.actor,
                    "closed_at": now.isoformat(),
                }
                db.add(
                    AuditLog(
                        actor=self.actor,
                        action="close_stale_discovery_run",
                        entity_type="discovery_run",
                        entity_id=str(run.id),
                        details_json={
                            "started_at": run.started_at.isoformat(),
                            "duration_seconds": run.duration_seconds,
                        },
                    )
                )
                repaired.append({"type": "discovery_run", "id": run.id, "action": "marked_failed"})
            if repaired:
                db.commit()
                logger.warning("watchdog repaired stale runs: {}", repaired)
        return {**self.inspect(db), "repaired": repaired}

    @staticmethod
    def _run_summary(run: DiscoveryRun | None) -> dict[str, Any] | None:
        if run is None:
            return None
        return {
            "id": run.id,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "symbols_scanned": run.symbols_scanned,
            "windows_sampled": run.windows_sampled,
            "accepted_patterns": run.accepted_patterns,
            "rejected_patterns": run.rejected_patterns,
        }

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
