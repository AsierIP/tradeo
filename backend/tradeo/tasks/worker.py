from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings, get_settings
from tradeo.db.init_db import init_db, seed_db
from tradeo.db.models import DiscoveryRun
from tradeo.db.session import SessionLocal
from tradeo.modules.intraday.flat_service import IntradayEodFlatService
from tradeo.ops.false_match_metrics import (
    collect_false_match_drift_metrics,
    persist_false_match_drift_report,
)
from tradeo.research.autonomous_research_director import ResearchDirector
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.schemas import ScanRequest
from tradeo.services.intraday_calendar import IntradayMarketCalendar
from tradeo.modules.shared.entry_scanner import (
    PatternEntryScanner,
    PatternEntryScannerSafetyError,
)
from tradeo.services.director_review_gate import DirectorReviewGate
from tradeo.services.data_provider import (
    universe_file_for_interval,
    universe_scope_for_interval,
)
from tradeo.services.reports import ReportService
from tradeo.services.runtime_status import write_intraday_session_status, write_worker_heartbeat
from tradeo.services.scanner import MarketScanner
from tradeo.services.self_improvement import SelfImprovementEngine
from tradeo.services.ops_alerts import record_internal_alert, record_job_failure
from tradeo.services.watchdog import SystemWatchdog

IntradayJobAction = Callable[[Settings], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class IntradayJobSpec:
    job_id: str
    func: Callable[[], None]
    enabled_attr: str
    trigger: str
    seconds_attr: str | None = None
    hour_attr: str | None = None
    minute_attr: str | None = None
    day_of_week: str = "mon-fri"


_INTRADAY_JOB_LOCKS: dict[str, Lock] = {}


def _record_job_failure(db, job_id: str, exc: BaseException) -> None:  # noqa: ANN001
    record_job_failure(db, job_id=job_id, exc=exc)


def scan_job() -> None:
    db = SessionLocal()
    try:
        response = MarketScanner().run(
            ScanRequest(limit=get_settings().scan_limit_default),
            db=db,
            store=True,
        )
        logger.info("scan complete: {}", response.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.exception("scan job failed: {}", exc)
        _record_job_failure(db, "market_scan", exc)
    finally:
        db.close()


def report_job() -> None:
    db = SessionLocal()
    try:
        pack = ReportService().generate_review_pack(db)
        logger.info("report generated: {}", pack.get("paths"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("report job failed: {}", exc)
        _record_job_failure(db, "daily_report", exc)
    finally:
        db.close()


def self_improvement_job() -> None:
    db = SessionLocal()
    try:
        result = SelfImprovementEngine().run_lab_cycle(db, max_symbols=25)
        logger.info("self-improvement result: {}", result.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.exception("self-improvement job failed: {}", exc)
        _record_job_failure(db, "weekly_self_improvement", exc)
    finally:
        db.close()


def discovery_job() -> None:
    db = SessionLocal()
    try:
        from tradeo.schemas import DiscoveryRunRequest

        settings = get_settings()
        if not settings.discovery_enabled:
            logger.info("discovery job skipped: discovery_enabled=false")
            return
        request = DiscoveryRunRequest(
            limit=settings.discovery_limit_default,
            period=settings.discovery_period,
            interval=settings.discovery_interval,
            max_total_windows=settings.discovery_max_total_windows,
            max_windows_per_symbol=settings.discovery_max_windows_per_symbol,
        )
        params = {
            "limit": request.limit,
            "period": request.period,
            "interval": request.interval,
            "max_total_windows": request.max_total_windows,
            "max_windows_per_symbol": request.max_windows_per_symbol,
            "universe_scope": universe_scope_for_interval(request.interval),
            "universe_file": universe_file_for_interval(settings, request.interval),
            "rr_levels": settings.discovery_rr_level_list,
            "window_sizes": settings.discovery_window_size_list,
            "forward_bars": settings.discovery_forward_bar_list,
        }
        running = db.query(DiscoveryRun).filter(DiscoveryRun.status == "running").first()
        if running:
            logger.info("discovery job skipped: run {} already running", running.id)
            return
        recent_cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=max(1, settings.discovery_scan_minutes)
        )
        recent = (
            db.query(DiscoveryRun)
            .filter(DiscoveryRun.status == "completed", DiscoveryRun.started_at >= recent_cutoff)
            .order_by(DiscoveryRun.started_at.desc())
            .first()
        )
        if recent and {k: recent.params_json.get(k) for k in params} == params:
            logger.info("discovery job skipped: recent equivalent run {}", recent.id)
            return
        result = PatternDiscoveryLabAgent().run(request, db)
        logger.info("pattern discovery result: {}", result.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.exception("pattern discovery job failed: {}", exc)
        _record_job_failure(db, "pattern_discovery_lab", exc)
    finally:
        db.close()


def novel_match_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.discovery_match_enabled:
            logger.info("novel pattern match job skipped: discovery_match_enabled=false")
            return
        result = NovelPatternMatcher().match_current(
            db,
            limit=settings.discovery_match_symbol_limit,
            max_patterns=settings.discovery_match_max_patterns,
            similarity_threshold=settings.discovery_match_similarity_threshold,
            store=True,
        )
        logger.info("novel pattern match result: {}", result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("novel pattern match job failed: {}", exc)
        _record_job_failure(db, "novel_pattern_matcher", exc)
    finally:
        db.close()


def research_director_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.research_director_enabled:
            logger.info("research director skipped: research_director_enabled=false")
            return
        result = ResearchDirector(settings).run(
            db,
            limit=settings.research_director_pattern_limit,
        )
        logger.info("research director result: {}", result.get("director_state", {}))
    except Exception as exc:  # noqa: BLE001
        logger.exception("research director failed: {}", exc)
        _record_job_failure(db, "research_director", exc)
    finally:
        db.close()


def laboratory_entry_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.laboratory_scanner_enabled:
            logger.info("laboratory entry scanner skipped: laboratory_scanner_enabled=false")
            return
        result = PatternEntryScanner(settings=settings).scan(db, module="laboratory")
        review_result = DirectorReviewGate.from_settings(settings).refresh(db)
        logger.info("laboratory entry scanner result: {}", result)
        logger.info("director review gate result: {}", review_result)
    except PatternEntryScannerSafetyError as exc:
        logger.warning("laboratory entry scanner blocked by safety gate: {}", exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("laboratory entry scanner failed: {}", exc)
        _record_job_failure(db, "laboratory_entry_scanner", exc)
    finally:
        db.close()


def fox_hunter_entry_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.fox_hunter_enabled:
            logger.info("fox hunter skipped: fox_hunter_enabled=false")
            return
        result = PatternEntryScanner(settings=settings).scan(db, module="fox_hunter")
        logger.info("fox hunter result: {}", result)
    except PatternEntryScannerSafetyError as exc:
        logger.warning("fox hunter blocked by safety gate: {}", exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("fox hunter failed: {}", exc)
        _record_job_failure(db, "fox_hunter_entry_scanner", exc)
    finally:
        db.close()


def reconciliation_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.reconciliation_enabled:
            logger.info("reconciliation skipped: reconciliation_enabled=false")
            return
        from tradeo.services.reconciliation import ReconciliationService

        result = ReconciliationService(settings=settings).reconcile(db)
        if result.get("divergences"):
            logger.error("reconciliation divergences: {}", result)
        else:
            logger.info("reconciliation result: {}", result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("reconciliation job failed: {}", exc)
        _record_job_failure(db, "ibkr_reconciliation", exc)
    finally:
        db.close()


def pattern_health_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.health_monitor_enabled:
            logger.info("pattern health monitor skipped: health_monitor_enabled=false")
            return
        from tradeo.services.pattern_health_monitor import PatternHealthMonitor

        result = PatternHealthMonitor(settings=settings).run(db)
        if result.get("decay_detected"):
            logger.warning("pattern health monitor result: {}", result)
        else:
            logger.info("pattern health monitor result: {}", result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("pattern health monitor job failed: {}", exc)
        _record_job_failure(db, "pattern_health_monitor", exc)
    finally:
        db.close()


def watchdog_job() -> None:
    db = SessionLocal()
    try:
        result = SystemWatchdog().repair(db)
        if result.get("repaired"):
            logger.warning("watchdog result: {}", result)
        else:
            logger.debug("watchdog ok: {}", result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("watchdog job failed: {}", exc)
        _record_job_failure(db, "system_watchdog", exc)
    finally:
        db.close()


def false_match_metrics_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.false_match_metrics_job_enabled:
            logger.info("false-match metrics job skipped: false_match_metrics_job_enabled=false")
            return
        report = collect_false_match_drift_metrics(
            db,
            high_fpr_threshold=settings.false_match_metrics_high_fpr_threshold,
        )
        persist_false_match_drift_report(db, report)
        logger.info(
            "false-match metrics report: patterns={} high_fpr={} drifted={}",
            report["pattern_count"],
            report["patterns_high_fpr"],
            report["patterns_drifted"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("false-match metrics job failed: {}", exc)
        _record_job_failure(db, "false_match_drift_metrics", exc)
    finally:
        db.close()


def intraday_universe_premarket_job() -> None:
    _run_intraday_job(
        "intraday_universe_premarket",
        "intraday_universe_enabled",
        lambda settings: _intraday_universe_placeholder(settings, bucket="premarket"),
    )


def intraday_universe_early_job() -> None:
    _run_intraday_job(
        "intraday_universe_early",
        "intraday_universe_enabled",
        lambda settings: _intraday_universe_placeholder(settings, bucket="early_session"),
    )


def intraday_data_sync_job() -> None:
    _run_intraday_job(
        "intraday_data_sync",
        "intraday_data_sync_enabled",
        lambda settings: _intraday_placeholder(
            settings,
            component="data_sync",
            reason="market_data_adapter_not_wired",
            details={"timeframes": settings.intraday_timeframe_list},
        ),
    )


def intraday_research_job() -> None:
    _run_intraday_job(
        "intraday_research",
        "intraday_research_enabled",
        lambda settings: _intraday_placeholder(
            settings,
            component="research",
            reason="research_worker_not_wired",
            details={"timeframes": settings.intraday_timeframe_list},
        ),
    )


def intraday_candidate_scan_job() -> None:
    _run_intraday_job(
        "intraday_candidate_scan",
        "intraday_candidate_scan_enabled",
        lambda settings: _intraday_placeholder(
            settings,
            component="candidate_scan",
            reason="candidate_scan_worker_not_wired",
            details={
                "timeframe": settings.intraday_execution_timeframe,
                "paper_enabled": settings.intraday_paper_enabled,
                "live_armed": settings.intraday_live_armed,
            },
        ),
    )


def intraday_observation_closer_job() -> None:
    _run_intraday_job(
        "intraday_observation_closer",
        "intraday_observation_closer_enabled",
        lambda settings: _intraday_placeholder(
            settings,
            component="observation_closer",
            reason="observation_closer_worker_not_wired",
            details={"timeframe": settings.intraday_execution_timeframe},
        ),
    )


def intraday_risk_heartbeat_job() -> None:
    _run_intraday_job(
        "intraday_risk_heartbeat",
        "intraday_risk_heartbeat_enabled",
        _intraday_risk_heartbeat,
    )


def intraday_reconciliation_job() -> None:
    _run_intraday_job(
        "intraday_reconciliation",
        "intraday_reconciliation_enabled",
        lambda settings: _intraday_placeholder(
            settings,
            component="reconciliation",
            reason="broker_reconciliation_adapter_not_wired",
            details={"live_armed": settings.intraday_live_armed},
        ),
    )


def intraday_eod_flat_job() -> None:
    _run_intraday_job(
        "intraday_eod_flat",
        "intraday_eod_flat_enabled",
        _intraday_eod_flat_preview,
    )


def register_intraday_jobs(scheduler: BackgroundScheduler, settings: Settings) -> list[str]:
    if not settings.intraday_enabled:
        return []

    registered: list[str] = []
    for spec in INTRADAY_JOB_SPECS:
        if not bool(getattr(settings, spec.enabled_attr)):
            continue
        _add_intraday_job(scheduler, spec, settings)
        registered.append(spec.job_id)
    return registered


def _add_intraday_job(
    scheduler: BackgroundScheduler,
    spec: IntradayJobSpec,
    settings: Settings,
) -> None:
    jitter = _intraday_jitter_seconds(settings)
    common = {
        "id": spec.job_id,
        "max_instances": 1,
        "coalesce": True,
        "misfire_grace_time": _intraday_misfire_grace_seconds(spec, settings),
        "replace_existing": True,
    }
    if spec.trigger == "interval":
        scheduler.add_job(
            spec.func,
            "interval",
            seconds=_positive_int(getattr(settings, spec.seconds_attr or ""), default=60),
            jitter=jitter,
            **common,
        )
        return

    if spec.trigger == "cron":
        scheduler.add_job(
            spec.func,
            CronTrigger(
                hour=_non_negative_int(getattr(settings, spec.hour_attr or ""), default=0),
                minute=_non_negative_int(getattr(settings, spec.minute_attr or ""), default=0),
                day_of_week=spec.day_of_week,
                jitter=jitter,
            ),
            **common,
        )
        return

    raise ValueError(f"unsupported intraday trigger: {spec.trigger}")


def _run_intraday_job(
    job_id: str,
    enabled_attr: str,
    action: IntradayJobAction,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.intraday_enabled:
        return _write_intraday_job_status(
            job_id,
            settings,
            status="noop",
            reason="intraday_disabled",
            details={"enabled_attr": enabled_attr},
        )
    if not bool(getattr(settings, enabled_attr)):
        return _write_intraday_job_status(
            job_id,
            settings,
            status="noop",
            reason=f"{enabled_attr}=false",
            details={"enabled_attr": enabled_attr},
        )

    lock = _INTRADAY_JOB_LOCKS.setdefault(job_id, Lock())
    if not lock.acquire(blocking=False):
        return _write_intraday_job_status(
            job_id,
            settings,
            status="skipped",
            reason="lock_busy",
            details={"enabled_attr": enabled_attr},
        )

    try:
        result = action(settings)
    except Exception as exc:  # noqa: BLE001 - worker heartbeat must still update.
        logger.exception("intraday job failed: {} {}", job_id, exc)
        result = {
            "status": "error",
            "reason": type(exc).__name__,
            "details": {"message": str(exc)},
        }
    finally:
        lock.release()

    return _write_intraday_job_status(
        job_id,
        settings,
        status=str(result.get("status") or "noop"),
        reason=result.get("reason"),
        details=dict(result.get("details") or {}),
    )


def _write_intraday_job_status(
    job_id: str,
    settings: Settings,
    *,
    status: str,
    reason: str | None,
    details: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "status": status,
        "reason": reason,
        "details": _intraday_safe_details(details),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_intraday_session_status(job_id, payload, settings)
    return payload


def _intraday_universe_placeholder(settings: Settings, *, bucket: str) -> dict[str, Any]:
    return _intraday_placeholder(
        settings,
        component="universe",
        reason="universe_market_metrics_adapter_not_wired",
        details={
            "bucket": bucket,
            "min_price": settings.intraday_min_price,
            "min_dollar_volume": settings.intraday_min_dollar_volume,
            "max_spread_bps": settings.intraday_max_spread_bps,
        },
    )


def _intraday_placeholder(
    settings: Settings,
    *,
    component: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "noop",
        "reason": reason,
        "details": {
            "component": component,
            "safe_placeholder": True,
            "shadow_enabled": settings.intraday_shadow_enabled,
            **(details or {}),
        },
    }


def _intraday_risk_heartbeat(settings: Settings) -> dict[str, Any]:
    return {
        "status": "ok",
        "reason": "heartbeat",
        "details": {
            "risk_per_trade_pct": settings.intraday_risk_per_trade_pct,
            "daily_loss_limit_pct": settings.intraday_daily_loss_limit_pct,
            "max_open_positions": settings.intraday_max_open_positions,
            "max_trades_per_day": settings.intraday_max_trades_per_day,
            "max_trades_per_symbol": settings.intraday_max_trades_per_symbol,
            "pacing_budget_per_10min": settings.intraday_pacing_budget_per_10min,
            "live_armed": settings.intraday_live_armed,
            "live_blockers": settings.intraday_live_config_blockers,
        },
    }


def _intraday_eod_flat_preview(settings: Settings) -> dict[str, Any]:
    if not settings.intraday_calendar_enabled:
        return {
            "status": "noop",
            "reason": "intraday_calendar_disabled",
            "details": {"preview": True, "safe_placeholder": True},
        }

    now = datetime.now(timezone.utc)
    calendar = IntradayMarketCalendar(timezone_name=settings.intraday_session_timezone)
    session = calendar.session_for(now)
    details: dict[str, Any] = {
        "preview": True,
        "safe_placeholder": True,
        "calendar_status": session.status,
        "session_date": session.session_date.isoformat(),
    }
    if not session.calendar_available:
        return {"status": "noop", "reason": session.reason, "details": details}
    if not session.is_open or session.cutoffs is None:
        return {"status": "noop", "reason": session.reason, "details": details}

    broker = _NoPositionFlatPreviewBroker()
    result = IntradayEodFlatService(broker).advance(
        now=now,
        no_new_entries_at=session.cutoffs.no_new_entries_at,
        cancel_entries_at=session.cutoffs.cancel_entries_at,
        force_flat_start_at=session.cutoffs.force_flat_start_at,
        hard_flat_deadline_at=session.cutoffs.hard_flat_deadline_at,
        preview=True,
    )
    details.update(
        {
            "flat_state": result.state.value,
            "orders_submitted": list(result.orders_submitted),
            "cancelled_order_ids": list(result.cancelled_order_ids),
            "unresolved_symbols": list(result.unresolved_symbols),
            "kill_switch_required": result.kill_switch_required,
            "reason_code": result.reason_code,
        }
    )
    return {
        "status": "blocked" if result.kill_switch_required else "ok",
        "reason": result.reason_code,
        "details": details,
    }


class _NoPositionFlatPreviewBroker:
    def cancel_open_entry_orders(self) -> list[str]:
        return []

    def snapshot_positions(self) -> list[Any]:
        return []

    def submit_reduce_only_exit(self, order: Any) -> str:
        return f"preview-{order.symbol}"

    def verify_flat_symbols(self, symbols: list[str]) -> bool:
        return not symbols


def _intraday_safe_details(details: dict[str, Any]) -> dict[str, Any]:
    blocked = ("password", "secret", "token", "key", "account", "username")
    safe: dict[str, Any] = {}
    for raw_key, value in details.items():
        key = str(raw_key)
        if any(part in key.lower() for part in blocked):
            safe[key] = "<redacted>" if value not in (None, "") else ""
        elif isinstance(value, datetime):
            safe[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, (list, tuple)):
            safe[key] = [
                item.isoformat() if isinstance(item, datetime) else item for item in value
            ]
        elif isinstance(value, dict):
            safe[key] = _intraday_safe_details(value)
        else:
            safe[key] = str(value)
    return safe


def _intraday_jitter_seconds(settings: Settings) -> int:
    return max(0, int(settings.intraday_job_jitter_seconds))


def _intraday_misfire_grace_seconds(spec: IntradayJobSpec, settings: Settings) -> int:
    if spec.trigger == "interval":
        seconds = _positive_int(getattr(settings, spec.seconds_attr or ""), default=60)
        return max(30, min(300, seconds * 2))
    return 300


def _positive_int(value: Any, *, default: int) -> int:
    number = _non_negative_int(value, default=default)
    return number if number > 0 else default


def _non_negative_int(value: Any, *, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, number)


INTRADAY_JOB_SPECS: tuple[IntradayJobSpec, ...] = (
    IntradayJobSpec(
        job_id="intraday_universe_premarket",
        func=intraday_universe_premarket_job,
        enabled_attr="intraday_universe_enabled",
        trigger="cron",
        hour_attr="intraday_universe_premarket_hour_utc",
        minute_attr="intraday_universe_premarket_minute_utc",
    ),
    IntradayJobSpec(
        job_id="intraday_universe_early",
        func=intraday_universe_early_job,
        enabled_attr="intraday_universe_enabled",
        trigger="cron",
        hour_attr="intraday_universe_early_hour_utc",
        minute_attr="intraday_universe_early_minute_utc",
    ),
    IntradayJobSpec(
        job_id="intraday_data_sync",
        func=intraday_data_sync_job,
        enabled_attr="intraday_data_sync_enabled",
        trigger="interval",
        seconds_attr="intraday_data_sync_interval_seconds",
    ),
    IntradayJobSpec(
        job_id="intraday_research",
        func=intraday_research_job,
        enabled_attr="intraday_research_enabled",
        trigger="interval",
        seconds_attr="intraday_candidate_scan_interval_seconds",
    ),
    IntradayJobSpec(
        job_id="intraday_candidate_scan",
        func=intraday_candidate_scan_job,
        enabled_attr="intraday_candidate_scan_enabled",
        trigger="interval",
        seconds_attr="intraday_candidate_scan_interval_seconds",
    ),
    IntradayJobSpec(
        job_id="intraday_observation_closer",
        func=intraday_observation_closer_job,
        enabled_attr="intraday_observation_closer_enabled",
        trigger="interval",
        seconds_attr="intraday_observation_closer_interval_seconds",
    ),
    IntradayJobSpec(
        job_id="intraday_risk_heartbeat",
        func=intraday_risk_heartbeat_job,
        enabled_attr="intraday_risk_heartbeat_enabled",
        trigger="interval",
        seconds_attr="intraday_risk_heartbeat_interval_seconds",
    ),
    IntradayJobSpec(
        job_id="intraday_reconciliation",
        func=intraday_reconciliation_job,
        enabled_attr="intraday_reconciliation_enabled",
        trigger="interval",
        seconds_attr="intraday_reconciliation_interval_seconds",
    ),
    IntradayJobSpec(
        job_id="intraday_eod_flat",
        func=intraday_eod_flat_job,
        enabled_attr="intraday_eod_flat_enabled",
        trigger="cron",
        hour_attr="intraday_eod_flat_hour_utc",
        minute_attr="intraday_eod_flat_minute_utc",
    ),
)


def scheduler_event_listener(event: JobExecutionEvent) -> None:
    db = SessionLocal()
    try:
        if event.code == EVENT_JOB_MISSED:
            record_internal_alert(
                db,
                source="scheduler",
                severity="warning",
                message=f"scheduler job missed: {event.job_id}",
                details={"job_id": event.job_id, "scheduled_run_time": str(event.scheduled_run_time)},
                entity_type="scheduler_job",
                entity_id=str(event.job_id),
            )
            return
        exc = getattr(event, "exception", None)
        if exc is not None:
            record_job_failure(db, job_id=str(event.job_id), exc=exc)
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    write_worker_heartbeat(settings)
    init_db()
    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_listener(scheduler_event_listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    if settings.scheduler_enabled:
        if settings.watchdog_enabled:
            watchdog_job()
            scheduler.add_job(
                watchdog_job,
                "interval",
                minutes=settings.watchdog_interval_minutes,
                id="system_watchdog",
                max_instances=1,
                coalesce=True,
            )
        scheduler.add_job(
            scan_job,
            "interval",
            minutes=settings.scheduler_scan_minutes,
            id="market_scan",
        )
        scheduler.add_job(
            report_job,
            CronTrigger(hour=settings.scheduler_report_hour_utc, minute=5, day_of_week="mon-fri"),
            id="daily_report",
        )
        scheduler.add_job(
            self_improvement_job,
            CronTrigger(hour=23, minute=15, day_of_week="fri"),
            id="weekly_self_improvement",
        )
        if settings.discovery_scheduler_enabled:
            if settings.discovery_scan_minutes >= 1440:
                # Daily data only gains information once per completed session.
                # Re-running intraday multiplies N_trials and burns IBKR pacing
                # without new bars, so schedule a single post-close run instead.
                scheduler.add_job(
                    discovery_job,
                    CronTrigger(
                        hour=settings.discovery_post_close_hour_utc,
                        minute=settings.discovery_post_close_minute_utc,
                        day_of_week="mon-fri",
                    ),
                    id="pattern_discovery_lab",
                    max_instances=1,
                    coalesce=True,
                )
            else:
                scheduler.add_job(
                    discovery_job,
                    "interval",
                    minutes=settings.discovery_scan_minutes,
                    id="pattern_discovery_lab",
                    max_instances=1,
                    coalesce=True,
                )
        if settings.discovery_match_enabled:
            scheduler.add_job(
                novel_match_job,
                "interval",
                minutes=settings.discovery_match_scan_minutes,
                id="novel_pattern_matcher",
                max_instances=1,
                coalesce=True,
            )
        if settings.research_director_enabled:
            research_director_job()
            scheduler.add_job(
                research_director_job,
                "interval",
                minutes=settings.research_director_interval_minutes,
                id="research_director",
                max_instances=1,
                coalesce=True,
            )
        if settings.laboratory_scanner_enabled:
            scheduler.add_job(
                laboratory_entry_job,
                "interval",
                minutes=settings.laboratory_scan_minutes,
                id="laboratory_entry_scanner",
                max_instances=1,
                coalesce=True,
            )
        if settings.fox_hunter_enabled:
            scheduler.add_job(
                fox_hunter_entry_job,
                "interval",
                minutes=settings.fox_hunter_scan_minutes,
                id="fox_hunter_entry_scanner",
                max_instances=1,
                coalesce=True,
            )
        if settings.reconciliation_enabled:
            scheduler.add_job(
                reconciliation_job,
                "interval",
                minutes=settings.reconciliation_interval_minutes,
                id="ibkr_reconciliation",
                max_instances=1,
                coalesce=True,
            )
        if settings.health_monitor_enabled:
            scheduler.add_job(
                pattern_health_job,
                "interval",
                minutes=settings.health_monitor_interval_minutes,
                id="pattern_health_monitor",
                max_instances=1,
                coalesce=True,
            )
        if settings.false_match_metrics_job_enabled:
            scheduler.add_job(
                false_match_metrics_job,
                CronTrigger(
                    hour=settings.false_match_metrics_hour_utc,
                    minute=settings.false_match_metrics_minute_utc,
                    day_of_week="mon-fri",
                ),
                id="false_match_drift_metrics",
                max_instances=1,
                coalesce=True,
            )
        register_intraday_jobs(scheduler, settings)
    scheduler.start()
    logger.info("Tradeo worker started. scheduler_enabled={}", settings.scheduler_enabled)
    try:
        while True:
            write_worker_heartbeat(settings)
            time.sleep(5)
    except KeyboardInterrupt:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
