from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import get_settings
from tradeo.db.init_db import init_db, seed_db
from tradeo.db.models import DiscoveryRun
from tradeo.db.session import SessionLocal
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
from tradeo.services.watchdog import SystemWatchdog


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
    finally:
        db.close()


def report_job() -> None:
    db = SessionLocal()
    try:
        pack = ReportService().generate_review_pack(db)
        logger.info("report generated: {}", pack.get("paths"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("report job failed: {}", exc)
    finally:
        db.close()


def self_improvement_job() -> None:
    db = SessionLocal()
    try:
        result = SelfImprovementEngine().run_lab_cycle(db, max_symbols=25)
        logger.info("self-improvement result: {}", result.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.exception("self-improvement job failed: {}", exc)
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
        review_result = DirectorReviewGate().refresh(db)
        logger.info("laboratory entry scanner result: {}", result)
        logger.info("director review gate result: {}", review_result)
    except PatternEntryScannerSafetyError as exc:
        logger.warning("laboratory entry scanner blocked by safety gate: {}", exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("laboratory entry scanner failed: {}", exc)
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
