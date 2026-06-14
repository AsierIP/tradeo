from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import get_settings
from tradeo.db.init_db import init_db, seed_db
from tradeo.db.models import DiscoveryRun
from tradeo.db.session import SessionLocal
from tradeo.ops.false_match_metrics import (
    collect_false_match_drift_metrics,
    persist_false_match_drift_report,
)
from tradeo.research.autonomous_research_director import ResearchDirector
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.schemas import ScanRequest
from tradeo.modules.shared.entry_scanner import (
    PatternEntryScanner,
    PatternEntryScannerSafetyError,
)
from tradeo.services.director_review_gate import DirectorReviewGate
from tradeo.services.reports import ReportService
from tradeo.services.runtime_status import write_worker_heartbeat
from tradeo.services.scanner import MarketScanner
from tradeo.services.self_improvement import SelfImprovementEngine
from tradeo.services.ops_alerts import record_internal_alert, record_job_failure
from tradeo.services.watchdog import SystemWatchdog


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
