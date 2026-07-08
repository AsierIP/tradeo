from __future__ import annotations

import atexit
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
import json
import multiprocessing
import os
import sys
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
from tradeo.modules.resource_policy.enforcement import (
    blocked_job_status,
    decide_with_market_session_policy,
)
from tradeo.modules.resource_policy.market_session_resource_policy import JobType
from tradeo.ops.false_match_metrics import (
    collect_false_match_drift_metrics,
    persist_false_match_drift_report,
)
from tradeo.research.intraday_context_filters import normalize_context_filter_spec
from tradeo.research.autonomous_research_director import ResearchDirector
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.schemas import DailyUniverseDiscoveryRunRequest, DiscoveryRunRequest, ScanRequest
from tradeo.services.intraday_calendar import IntradayMarketCalendar
from tradeo.modules.shared.entry_scanner import (
    PatternEntryScanner,
    PatternEntryScannerSafetyError,
)
from tradeo.services.director_review_gate import DirectorReviewGate
from tradeo.services.data_provider import (
    is_daily_interval,
    pick_symbols,
    universe_file_for_interval,
    universe_scope_for_interval,
)
from tradeo.services.daily_discovery_orchestrator import DailyDiscoveryOrchestrator
from tradeo.services.reports import ReportService
from tradeo.services.runtime_status import write_intraday_session_status, write_worker_heartbeat
from tradeo.services.scanner import MarketScanner
from tradeo.services.self_improvement import SelfImprovementEngine
from tradeo.services.ops_alerts import record_internal_alert, record_job_failure
from tradeo.services.provider_factory import get_market_data_provider
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


@dataclass(frozen=True, slots=True)
class IntradayResearchProcessJob:
    timeframe: str
    chunk_index: int
    chunk_count: int
    symbols: tuple[str, ...] | None
    pool_run_id: str
    estimated_cost: int = 0
    allow_recent_duplicates: bool = False
    store_rejected: bool | None = False


_INTRADAY_JOB_LOCKS: dict[str, Lock] = {}
_INTRADAY_RESEARCH_PROCESS_POOL: ProcessPoolExecutor | None = None
_INTRADAY_RESEARCH_PROCESS_POOL_KEY: tuple[int, int, str | None] | None = None
_INTRADAY_RESEARCH_PROCESS_POOL_LOCK = Lock()
_INTRADAY_RESEARCH_PROCESS_WORKER_RUN_ID: str | None = None
_INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV = "TRADEO_INTRADAY_RESEARCH_PROCESS_START_METHOD"
_INTRADAY_RESEARCH_ADAPTIVE_CHUNKS_ENV = "TRADEO_INTRADAY_RESEARCH_ADAPTIVE_CHUNKS"
_NATIVE_THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
_INTRADAY_RESOURCE_POLICY_JOB_TYPES = {
    "intraday_universe_premarket": JobType.LARGE_SCANNER,
    "intraday_universe_early": JobType.LARGE_SCANNER,
    "intraday_data_sync": JobType.RESEARCH_HEAVY,
    "intraday_research": JobType.RESEARCH_HEAVY,
    "intraday_research_process_pool": JobType.RESEARCH_HEAVY,
    "intraday_candidate_scan": JobType.LARGE_SCANNER,
    "intraday_observation_closer": JobType.INTRADAY_LAB,
}


def _record_job_failure(db, job_id: str, exc: BaseException) -> None:  # noqa: ANN001
    record_job_failure(db, job_id=job_id, exc=exc)


def _resource_policy_blocks_job(
    job_id: str,
    job_type: str,
    owner: str,
    settings: Settings,
) -> bool:
    decision = decide_with_market_session_policy(job_type, owner, settings=settings)
    if decision.allowed:
        return False
    logger.warning(
        "job blocked by resource policy: job_id={} job_type={} reason={}",
        job_id,
        job_type,
        decision.deny_reason,
    )
    return True


def scan_job() -> None:
    settings = get_settings()
    if _resource_policy_blocks_job("market_scan", JobType.LARGE_SCANNER, "scanner", settings):
        return
    db = SessionLocal()
    try:
        response = MarketScanner().run(
            ScanRequest(limit=settings.scan_limit_default),
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
    settings = get_settings()
    if _resource_policy_blocks_job(
        "weekly_self_improvement",
        JobType.HEAVY_BACKTEST,
        "research",
        settings,
    ):
        return
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
    settings = get_settings()
    if not settings.discovery_enabled:
        logger.info("discovery job skipped: discovery_enabled=false")
        return
    if _resource_policy_blocks_job(
        "pattern_discovery_lab",
        JobType.RESEARCH_HEAVY,
        "research",
        settings,
    ):
        return
    if is_daily_interval(settings.discovery_interval):
        request = DailyUniverseDiscoveryRunRequest(
            limit=settings.discovery_limit_default,
            period=settings.discovery_period,
            interval=settings.discovery_interval,
            max_total_windows=settings.discovery_max_total_windows,
            max_windows_per_symbol=settings.discovery_max_windows_per_symbol,
            daily_cap_segments=settings.daily_universe_cap_segment_list,
            parallel=False,
            skip_recent_seconds=max(60, int(settings.discovery_scan_minutes) * 60),
        )
        result = DailyDiscoveryOrchestrator(settings=settings).run(request)
        logger.info("daily universe discovery result: {}", result.model_dump())
        return
    db = SessionLocal()
    try:
        request = DiscoveryRunRequest(
            limit=settings.discovery_limit_default,
            period=settings.discovery_period,
            interval=settings.discovery_interval,
            max_total_windows=settings.discovery_max_total_windows,
            max_windows_per_symbol=settings.discovery_max_windows_per_symbol,
        )
        params = {
            "cadence": "daily",
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
        running = db.query(DiscoveryRun).filter(DiscoveryRun.status == "running").all()
        matching_running = next(
            (run for run in running if _discovery_params_match(run.params_json or {}, params)),
            None,
        )
        if matching_running:
            logger.info("discovery job skipped: equivalent run {} already running", matching_running.id)
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
    settings = get_settings()
    if not settings.discovery_match_enabled:
        logger.info("novel pattern match job skipped: discovery_match_enabled=false")
        return
    if _resource_policy_blocks_job(
        "novel_pattern_matcher",
        JobType.LARGE_SCANNER,
        "research",
        settings,
    ):
        return
    db = SessionLocal()
    try:
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
    settings = get_settings()
    if not settings.research_director_enabled:
        logger.info("research director skipped: research_director_enabled=false")
        return
    if _resource_policy_blocks_job(
        "research_director",
        JobType.RESEARCH_HEAVY,
        "research",
        settings,
    ):
        return
    db = SessionLocal()
    try:
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


def daily_paper_entry_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        if not settings.daily_paper_execution_enabled:
            logger.info("daily paper entry scanner skipped: daily_paper_execution_enabled=false")
            return
        result = PatternEntryScanner(settings=settings).scan(db, module="daily")
        logger.info("daily paper entry scanner result: {}", result)
    except PatternEntryScannerSafetyError as exc:
        logger.warning("daily paper entry scanner blocked by safety gate: {}", exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("daily paper entry scanner failed: {}", exc)
        _record_job_failure(db, "daily_paper_entry_scanner", exc)
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
        _run_intraday_data_sync,
    )


def intraday_research_job() -> None:
    _run_intraday_job(
        "intraday_research",
        "intraday_research_enabled",
        _run_intraday_research,
    )


def intraday_research_process_pool_job() -> None:
    _run_intraday_job(
        "intraday_research_process_pool",
        "intraday_research_enabled",
        _run_intraday_research_process_pool,
    )


def intraday_research_timeframe_job(timeframe: str) -> None:
    safe_timeframe = timeframe.replace("/", "_").replace(" ", "_")
    _run_intraday_job(
        f"intraday_research_{safe_timeframe}",
        "intraday_research_enabled",
        lambda settings: _run_intraday_research(settings, timeframes=[timeframe]),
    )


def intraday_research_timeframe_chunk_job(timeframe: str, chunk_index: int, chunk_count: int) -> None:
    safe_timeframe = timeframe.replace("/", "_").replace(" ", "_")
    _run_intraday_job(
        f"intraday_research_{safe_timeframe}_chunk_{chunk_index + 1}_of_{chunk_count}",
        "intraday_research_enabled",
        lambda settings: _run_intraday_research(
            settings,
            timeframes=[timeframe],
            symbol_chunk=(chunk_index, chunk_count),
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
        if spec.job_id == "intraday_research" and settings.intraday_research_parallel_timeframes_enabled:
            if settings.intraday_research_process_pool_enabled:
                pool_spec = IntradayJobSpec(
                    job_id="intraday_research_process_pool",
                    func=intraday_research_process_pool_job,
                    enabled_attr=spec.enabled_attr,
                    trigger=spec.trigger,
                    seconds_attr=spec.seconds_attr,
                )
                _add_intraday_job(scheduler, pool_spec, settings)
                registered.append(pool_spec.job_id)
                continue
            chunk_count = _intraday_research_parallel_symbol_chunks(settings)
            for timeframe in settings.intraday_timeframe_list:
                if chunk_count <= 1:
                    safe_timeframe = timeframe.replace("/", "_").replace(" ", "_")
                    timeframe_spec = IntradayJobSpec(
                        job_id=f"intraday_research_{safe_timeframe}",
                        func=lambda tf=timeframe: intraday_research_timeframe_job(tf),
                        enabled_attr=spec.enabled_attr,
                        trigger=spec.trigger,
                        seconds_attr=spec.seconds_attr,
                    )
                    _add_intraday_job(scheduler, timeframe_spec, settings)
                    registered.append(timeframe_spec.job_id)
                    continue
                for chunk_index in range(chunk_count):
                    safe_timeframe = timeframe.replace("/", "_").replace(" ", "_")
                    chunk_spec = IntradayJobSpec(
                        job_id=f"intraday_research_{safe_timeframe}_chunk_{chunk_index + 1}_of_{chunk_count}",
                        func=lambda tf=timeframe, idx=chunk_index, count=chunk_count: (
                            intraday_research_timeframe_chunk_job(tf, idx, count)
                        ),
                        enabled_attr=spec.enabled_attr,
                        trigger=spec.trigger,
                        seconds_attr=spec.seconds_attr,
                    )
                    _add_intraday_job(scheduler, chunk_spec, settings)
                    registered.append(chunk_spec.job_id)
            continue
        _add_intraday_job(scheduler, spec, settings)
        registered.append(spec.job_id)
    return registered


def register_daily_paper_jobs(scheduler: BackgroundScheduler, settings: Settings) -> list[str]:
    if not settings.daily_paper_execution_enabled:
        return []

    job_id = "daily_paper_entry_scanner"
    common = {
        "id": job_id,
        "max_instances": 1,
        "coalesce": True,
    }
    if settings.daily_paper_scan_minutes >= 1440:
        scheduler.add_job(
            daily_paper_entry_job,
            CronTrigger(
                hour=settings.daily_paper_post_close_hour_utc,
                minute=settings.daily_paper_post_close_minute_utc,
                day_of_week="mon-fri",
            ),
            **common,
        )
    else:
        scheduler.add_job(
            daily_paper_entry_job,
            "interval",
            minutes=settings.daily_paper_scan_minutes,
            **common,
        )
    return [job_id]


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
    policy_job_type = _resource_policy_job_type(job_id)
    if policy_job_type is not None:
        decision = decide_with_market_session_policy(
            policy_job_type,
            _resource_policy_owner(job_id),
            settings=settings,
        )
        if not decision.allowed:
            blocked = blocked_job_status(decision)
            return _write_intraday_job_status(
                job_id,
                settings,
                status=blocked["status"],
                reason=blocked["reason"],
                details={**dict(blocked["details"]), "enabled_attr": enabled_attr},
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


def _resource_policy_job_type(job_id: str) -> str | None:
    if job_id in _INTRADAY_RESOURCE_POLICY_JOB_TYPES:
        return _INTRADAY_RESOURCE_POLICY_JOB_TYPES[job_id]
    if job_id.startswith("intraday_research_"):
        return JobType.RESEARCH_HEAVY
    return None


def _resource_policy_owner(job_id: str) -> str:
    if "research" in job_id:
        return "intraday_research"
    if "candidate_scan" in job_id:
        return "intraday_scanner"
    if "universe" in job_id:
        return "intraday_scanner"
    if "observation" in job_id:
        return "intraday_lab"
    return "intraday_worker"


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


def _run_intraday_data_sync(settings: Settings) -> dict[str, Any]:
    timeframes = settings.intraday_timeframe_list
    if not timeframes:
        return {
            "status": "noop",
            "reason": "intraday_timeframes_empty",
            "details": {"component": "data_sync"},
        }

    provider = get_market_data_provider(cache_refresh_enabled=True)
    fetched = 0
    failed: list[dict[str, str]] = []
    symbols_by_timeframe: dict[str, int] = {}
    for timeframe in timeframes:
        symbols = pick_symbols(
            limit=settings.intraday_research_limit_default,
            interval=timeframe,
            universe_file=universe_file_for_interval(settings, timeframe),
        )
        symbols_by_timeframe[timeframe] = len(symbols)
        for symbol in symbols:
            try:
                provider.fetch_ohlcv(
                    symbol,
                    period=settings.intraday_research_period,
                    interval=timeframe,
                )
                fetched += 1
            except Exception as exc:  # noqa: BLE001 - keep warming the rest of the universe.
                failed.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    status = "ok" if not failed else "degraded"
    return {
        "status": status,
        "reason": "intraday_data_sync_completed",
        "details": {
            "component": "data_sync",
            "safe_placeholder": False,
            "timeframes": timeframes,
            "symbols_by_timeframe": symbols_by_timeframe,
            "fetched": fetched,
            "failed": len(failed),
            "failures": failed[:10],
            "period": settings.intraday_research_period,
        },
    }


def _run_intraday_research(
    settings: Settings,
    *,
    timeframes: list[str] | None = None,
    symbol_chunk: tuple[int, int] | None = None,
    chunk_symbols: list[str] | tuple[str, ...] | None = None,
    store_rejected: bool | None = None,
    allow_recent_duplicates: bool = False,
) -> dict[str, Any]:
    timeframes = timeframes or settings.intraday_timeframe_list
    if not timeframes:
        return {
            "status": "noop",
            "reason": "intraday_timeframes_empty",
            "details": {"component": "research"},
        }

    db = SessionLocal()
    runs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    try:
        running = db.query(DiscoveryRun).filter(DiscoveryRun.status == "running").all()
        recent_cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=max(60, settings.intraday_research_interval_seconds)
        )
        recent_completed = (
            db.query(DiscoveryRun)
            .filter(DiscoveryRun.status == "completed", DiscoveryRun.started_at >= recent_cutoff)
            .order_by(DiscoveryRun.started_at.desc())
            .all()
        )
        for timeframe in timeframes:
            resolved_chunk_symbols = None
            if symbol_chunk is not None:
                resolved_chunk_symbols = (
                    list(chunk_symbols)
                    if chunk_symbols is not None
                    else _intraday_research_symbols_for_chunk(settings, timeframe, symbol_chunk)
                )
            if symbol_chunk is not None and not resolved_chunk_symbols:
                skipped.append(
                    {
                        "timeframe": timeframe,
                        "reason": "empty_symbol_chunk",
                        "chunk": _intraday_chunk_details(symbol_chunk, []),
                    }
                )
                continue
            request = _intraday_research_request(
                settings,
                timeframe,
                symbols=resolved_chunk_symbols,
                store_rejected=store_rejected,
            )
            expected = _intraday_research_expected_params(settings, request)
            if not allow_recent_duplicates and any(
                _discovery_params_match(run.params_json or {}, expected) for run in running
            ):
                skipped.append(
                    {
                        "timeframe": timeframe,
                        "reason": "run_already_running",
                        "chunk": _intraday_chunk_details(symbol_chunk, resolved_chunk_symbols),
                    }
                )
                continue
            if not allow_recent_duplicates and any(
                _discovery_params_match(run.params_json or {}, expected)
                for run in recent_completed
            ):
                skipped.append(
                    {
                        "timeframe": timeframe,
                        "reason": "recent_equivalent_run",
                        "chunk": _intraday_chunk_details(symbol_chunk, resolved_chunk_symbols),
                    }
                )
                continue
            completed_equivalent_run = (
                None
                if allow_recent_duplicates
                or not settings.intraday_research_skip_completed_equivalent_runs
                else _completed_equivalent_discovery_run(db, expected)
            )
            if completed_equivalent_run is not None:
                skipped.append(
                    {
                        "timeframe": timeframe,
                        "reason": "completed_equivalent_run",
                        "run_id": completed_equivalent_run.id,
                        "chunk": _intraday_chunk_details(symbol_chunk, resolved_chunk_symbols),
                    }
                )
                continue

            provider = get_market_data_provider(
                cache_refresh_enabled=settings.intraday_research_refresh_market_data_enabled
            )
            result = PatternDiscoveryLabAgent(settings=settings, provider=provider).run(request, db)
            runs.append(
                {
                    "timeframe": timeframe,
                    "chunk": _intraday_chunk_details(symbol_chunk, resolved_chunk_symbols),
                    "run_id": result.run_id,
                    "symbols_scanned": result.symbols_scanned,
                    "windows_sampled": result.windows_sampled,
                    "clusters_evaluated": result.clusters_evaluated,
                    "accepted_patterns": result.accepted_patterns,
                    "rejected_patterns": result.rejected_patterns,
                    "stored_patterns": result.stored_patterns,
                    "actual_resolved_params": result.actual_resolved_params,
                    "actual_params_source": "PatternDiscoveryLabAgent._resolve_params",
                }
            )
    finally:
        db.close()

    return {
        "status": "ok",
        "reason": "intraday_research_completed" if runs else "intraday_research_waiting",
        "details": {
            "component": "research",
            "safe_placeholder": False,
            "timeframes": timeframes,
            "symbol_chunk": _intraday_chunk_details(symbol_chunk, None),
            "runs": runs,
            "skipped": skipped,
            "period": settings.intraday_research_period,
            "limit": settings.intraday_research_limit_default,
            "interval_seconds": settings.intraday_research_interval_seconds,
            "allow_recent_duplicates": allow_recent_duplicates,
        },
    }


def _run_intraday_research_process_pool(
    settings: Settings,
    *,
    allow_recent_duplicates: bool = False,
    store_rejected: bool | None = False,
) -> dict[str, Any]:
    started = time.monotonic()
    jobs = _intraday_research_process_jobs(
        settings,
        allow_recent_duplicates=allow_recent_duplicates,
        store_rejected=store_rejected,
    )
    if not jobs:
        return {
            "status": "noop",
            "reason": "intraday_research_process_pool_empty",
            "details": {"component": "research", "process_pool": True},
        }

    chunk_count = jobs[0].chunk_count
    max_workers = min(max(1, int(settings.intraday_research_process_workers or 1)), len(jobs))
    native_threads = max(1, int(settings.intraday_research_native_threads_per_process or 1))
    start_method = _intraday_research_process_start_method()
    runs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    worker_results: list[dict[str, Any]] = []
    pool_broken = False

    try:
        executor = _intraday_research_process_executor(max_workers, native_threads)
        futures = {
            executor.submit(_run_intraday_research_process_worker, job): (submit_order, job)
            for submit_order, job in enumerate(jobs)
        }
    except BrokenProcessPool:
        _shutdown_intraday_research_process_pool()
        executor = _intraday_research_process_executor(max_workers, native_threads)
        futures = {
            executor.submit(_run_intraday_research_process_worker, job): (submit_order, job)
            for submit_order, job in enumerate(jobs)
        }

    for future in as_completed(futures):
        submit_order, job = futures[future]
        try:
            result = future.result()
        except Exception as exc:  # noqa: BLE001 - report the failed chunk and continue.
            if isinstance(exc, BrokenProcessPool):
                pool_broken = True
            logger.exception(
                "intraday research process chunk failed: {} chunk {}/{} {}",
                job.timeframe,
                job.chunk_index + 1,
                job.chunk_count,
                exc,
            )
            errors.append(
                {
                    "timeframe": job.timeframe,
                    "chunk": f"{job.chunk_index + 1}_of_{job.chunk_count}",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        details = dict(result.get("details") or {})
        runs.extend(list(details.get("runs") or []))
        skipped.extend(list(details.get("skipped") or []))
        process_job = details.get("process_job")
        if isinstance(process_job, dict):
            process_job["submitted_order"] = submit_order
            process_job["completed_order"] = len(worker_results)
            worker_results.append(process_job)

    if pool_broken:
        _shutdown_intraday_research_process_pool()

    status = "ok" if not errors else ("degraded" if runs or skipped else "error")
    return {
        "status": status,
        "reason": "intraday_research_process_pool_completed",
        "details": {
            "component": "research",
            "process_pool": True,
            "process_workers": max_workers,
            "jobs": len(jobs),
            "chunks": chunk_count,
            "configured_chunks": _intraday_research_parallel_symbol_chunks(settings),
            "adaptive_chunks": _intraday_research_adaptive_chunks_enabled(),
            "native_threads_per_process": native_threads,
            "process_start_method": start_method or "default",
            "allow_recent_duplicates": allow_recent_duplicates,
            "store_rejected": store_rejected,
            "runs": runs,
            "skipped": skipped,
            "errors": errors,
            "worker_results": sorted(
                worker_results,
                key=lambda item: (
                    str(item.get("timeframe") or ""),
                    int(item.get("chunk_index") or 0),
                ),
            ),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        },
    }


def _run_intraday_research_process_worker(
    job: IntradayResearchProcessJob | tuple[str, int, int],
) -> dict[str, Any]:
    started = time.monotonic()
    process_job = _coerce_intraday_research_process_job(job)
    cache_clear = getattr(get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    settings = get_settings()
    native_threads = max(1, int(settings.intraday_research_native_threads_per_process or 1))
    _set_intraday_research_native_threads(native_threads)
    _reset_intraday_research_process_worker_state(process_job.pool_run_id)

    try:
        from threadpoolctl import threadpool_limits
    except ImportError:
        result = _run_intraday_research(
            settings,
            timeframes=[process_job.timeframe],
            symbol_chunk=(process_job.chunk_index, process_job.chunk_count),
            chunk_symbols=process_job.symbols,
            store_rejected=process_job.store_rejected,
            allow_recent_duplicates=process_job.allow_recent_duplicates,
        )
        return _intraday_research_process_worker_result(result, process_job, started)

    with threadpool_limits(limits=native_threads):
        result = _run_intraday_research(
            settings,
            timeframes=[process_job.timeframe],
            symbol_chunk=(process_job.chunk_index, process_job.chunk_count),
            chunk_symbols=process_job.symbols,
            store_rejected=process_job.store_rejected,
            allow_recent_duplicates=process_job.allow_recent_duplicates,
        )
    return _intraday_research_process_worker_result(result, process_job, started)


def _intraday_research_process_jobs(
    settings: Settings,
    *,
    allow_recent_duplicates: bool = False,
    store_rejected: bool | None = False,
) -> list[IntradayResearchProcessJob]:
    chunk_count = _intraday_research_process_chunk_count(settings)
    pool_run_id = f"{os.getpid()}:{time.monotonic_ns()}"
    jobs: list[IntradayResearchProcessJob] = []
    timeframe_order = {
        timeframe: index for index, timeframe in enumerate(settings.intraday_timeframe_list)
    }
    for timeframe in settings.intraday_timeframe_list:
        symbol_chunks = _intraday_research_process_symbol_chunks(settings, timeframe, chunk_count)
        for chunk_index, symbols, estimated_cost in symbol_chunks:
            jobs.append(
                IntradayResearchProcessJob(
                    timeframe=timeframe,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    symbols=tuple(symbols or ()),
                    pool_run_id=pool_run_id,
                    estimated_cost=estimated_cost,
                    allow_recent_duplicates=allow_recent_duplicates,
                    store_rejected=store_rejected,
                )
            )
    return _intraday_research_order_process_jobs(jobs, timeframe_order)


def _intraday_research_order_process_jobs(
    jobs: list[IntradayResearchProcessJob],
    timeframe_order: dict[str, int],
) -> list[IntradayResearchProcessJob]:
    cost_aware = any(int(job.estimated_cost) > len(job.symbols or ()) for job in jobs)
    return sorted(
        jobs,
        key=lambda job: (
            -int(job.estimated_cost) if cost_aware else int(job.chunk_index),
            int(job.chunk_index) if cost_aware else int(timeframe_order.get(job.timeframe, 0)),
            int(timeframe_order.get(job.timeframe, 0)) if cost_aware else 0,
        ),
    )


def _intraday_research_common_expected_params(settings: Settings) -> dict[str, Any]:
    context_spec = _intraday_research_context_filter_spec()
    return {
        "cadence": "intraday",
        "limit": settings.intraday_research_limit_default,
        "period": settings.intraday_research_period,
        "window_sizes": settings.intraday_research_window_size_list,
        "forward_bars": settings.intraday_research_forward_bar_list,
        "stride": settings.intraday_research_stride,
        "max_total_windows": settings.intraday_research_max_total_windows,
        "max_windows_per_symbol": settings.intraday_research_max_windows_per_symbol,
        "min_cluster_size": settings.intraday_research_min_cluster_size,
        "max_clusters_per_window": settings.intraday_research_max_clusters_per_window,
        "vwap_condition": _intraday_research_vwap_condition(),
        "vwap_side_bias": _optional_env("TRADEO_INTRADAY_RESEARCH_VWAP_SIDE_BIAS"),
        "vwap_max_distance_bps": _optional_float_env("TRADEO_INTRADAY_RESEARCH_VWAP_MAX_DISTANCE_BPS"),
        "vwap_min_slope_bps": _optional_float_env("TRADEO_INTRADAY_RESEARCH_VWAP_MIN_SLOPE_BPS"),
        "session_filter": context_spec.session_filter,
        "cost_filter": context_spec.cost_filter,
        "max_execution_cost_r": context_spec.max_execution_cost_r,
        "min_samples": settings.intraday_research_min_samples,
        "min_effective_samples": settings.intraday_research_min_effective_samples,
        "min_symbols": settings.intraday_research_min_symbols,
        "min_years": settings.intraday_research_min_years,
        "universe_file": settings.intraday_universe_file,
    }


def _coerce_intraday_research_process_job(
    job: IntradayResearchProcessJob | tuple[str, int, int],
) -> IntradayResearchProcessJob:
    if isinstance(job, IntradayResearchProcessJob):
        return job
    timeframe, chunk_index, chunk_count = job
    return IntradayResearchProcessJob(
        timeframe=timeframe,
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        symbols=None,
        pool_run_id="",
        allow_recent_duplicates=False,
        store_rejected=False,
    )


def _intraday_research_process_executor(
    max_workers: int,
    native_threads: int,
) -> ProcessPoolExecutor:
    global _INTRADAY_RESEARCH_PROCESS_POOL, _INTRADAY_RESEARCH_PROCESS_POOL_KEY
    start_method = _intraday_research_process_start_method()
    key = (int(max_workers), int(native_threads), start_method)
    with _INTRADAY_RESEARCH_PROCESS_POOL_LOCK:
        if (
            _INTRADAY_RESEARCH_PROCESS_POOL is not None
            and _INTRADAY_RESEARCH_PROCESS_POOL_KEY == key
        ):
            return _INTRADAY_RESEARCH_PROCESS_POOL
        if _INTRADAY_RESEARCH_PROCESS_POOL is not None:
            _INTRADAY_RESEARCH_PROCESS_POOL.shutdown(wait=True, cancel_futures=False)
        executor_kwargs: dict[str, Any] = {
            "max_workers": max_workers,
            "initializer": _intraday_research_process_initializer,
            "initargs": (native_threads,),
        }
        if start_method is not None:
            executor_kwargs["mp_context"] = multiprocessing.get_context(start_method)
        _INTRADAY_RESEARCH_PROCESS_POOL = ProcessPoolExecutor(**executor_kwargs)
        _INTRADAY_RESEARCH_PROCESS_POOL_KEY = key
        return _INTRADAY_RESEARCH_PROCESS_POOL


def _intraday_research_process_start_method() -> str | None:
    requested = os.getenv(_INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV, "auto").strip().lower()
    available = multiprocessing.get_all_start_methods()
    if requested in {"", "auto"}:
        if sys.platform.startswith("linux") and "fork" in available:
            return "fork"
        return None
    if requested in {"default", "none"}:
        return None
    if requested in available:
        return requested
    logger.warning(
        "unsupported intraday research process start method {}; using Python default",
        requested,
    )
    return None


def _shutdown_intraday_research_process_pool() -> None:
    global _INTRADAY_RESEARCH_PROCESS_POOL, _INTRADAY_RESEARCH_PROCESS_POOL_KEY
    with _INTRADAY_RESEARCH_PROCESS_POOL_LOCK:
        if _INTRADAY_RESEARCH_PROCESS_POOL is not None:
            _INTRADAY_RESEARCH_PROCESS_POOL.shutdown(wait=False, cancel_futures=True)
        _INTRADAY_RESEARCH_PROCESS_POOL = None
        _INTRADAY_RESEARCH_PROCESS_POOL_KEY = None


def _intraday_research_process_initializer(native_threads: int) -> None:
    _set_intraday_research_native_threads(native_threads)
    _reset_intraday_research_process_db_state()
    cache_clear = getattr(get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def _set_intraday_research_native_threads(native_threads: int) -> None:
    thread_count = str(max(1, int(native_threads)))
    for env_var in _NATIVE_THREAD_ENV_VARS:
        os.environ[env_var] = thread_count


def _reset_intraday_research_process_worker_state(pool_run_id: str) -> None:
    global _INTRADAY_RESEARCH_PROCESS_WORKER_RUN_ID
    if not pool_run_id or _INTRADAY_RESEARCH_PROCESS_WORKER_RUN_ID == pool_run_id:
        return
    _reset_intraday_research_process_db_state()
    _INTRADAY_RESEARCH_PROCESS_WORKER_RUN_ID = pool_run_id


def _reset_intraday_research_process_db_state() -> None:
    try:
        from tradeo.db.session import engine

        engine.dispose(close=False)
    except Exception as exc:  # noqa: BLE001 - DB reconnect isolation is best effort.
        logger.debug("intraday research process DB reset skipped: {}", exc)


def _intraday_research_process_worker_result(
    result: dict[str, Any],
    job: IntradayResearchProcessJob,
    started: float,
) -> dict[str, Any]:
    details = dict(result.get("details") or {})
    details["process_job"] = {
        "timeframe": job.timeframe,
        "chunk_index": job.chunk_index,
        "chunk_number": job.chunk_index + 1,
        "chunk_count": job.chunk_count,
        "symbols": len(job.symbols or ()),
        "estimated_cost": int(job.estimated_cost),
        "allow_recent_duplicates": job.allow_recent_duplicates,
        "store_rejected": job.store_rejected,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    return {
        **result,
        "details": details,
    }


atexit.register(_shutdown_intraday_research_process_pool)


def _intraday_research_request(
    settings: Settings,
    timeframe: str,
    *,
    symbols: list[str] | None = None,
    store_rejected: bool | None = None,
) -> DiscoveryRunRequest:
    context_spec = _intraday_research_context_filter_spec()
    return DiscoveryRunRequest(
        limit=settings.intraday_research_limit_default,
        symbols=symbols,
        period=settings.intraday_research_period,
        interval=timeframe,
        window_sizes=settings.intraday_research_window_size_list,
        forward_bars=settings.intraday_research_forward_bar_list,
        stride=settings.intraday_research_stride,
        max_total_windows=settings.intraday_research_max_total_windows,
        max_windows_per_symbol=settings.intraday_research_max_windows_per_symbol,
        min_cluster_size=settings.intraday_research_min_cluster_size,
        max_clusters_per_window=settings.intraday_research_max_clusters_per_window,
        store_rejected=store_rejected,
        vwap_condition=_intraday_research_vwap_condition(),
        vwap_side_bias=_optional_env("TRADEO_INTRADAY_RESEARCH_VWAP_SIDE_BIAS"),
        vwap_max_distance_bps=_optional_float_env("TRADEO_INTRADAY_RESEARCH_VWAP_MAX_DISTANCE_BPS"),
        vwap_min_slope_bps=_optional_float_env("TRADEO_INTRADAY_RESEARCH_VWAP_MIN_SLOPE_BPS"),
        session_filter=context_spec.session_filter,
        cost_filter=context_spec.cost_filter,
        max_execution_cost_r=context_spec.max_execution_cost_r,
    )


def _intraday_research_expected_params(
    settings: Settings,
    request: DiscoveryRunRequest,
) -> dict[str, Any]:
    return {
        "cadence": "intraday",
        "limit": request.limit,
        "period": request.period,
        "interval": request.interval,
        "window_sizes": request.window_sizes,
        "forward_bars": request.forward_bars,
        "stride": request.stride,
        "max_total_windows": request.max_total_windows,
        "max_windows_per_symbol": request.max_windows_per_symbol,
        "min_cluster_size": request.min_cluster_size,
        "max_clusters_per_window": request.max_clusters_per_window,
        "vwap_condition": request.vwap_condition or "none",
        "vwap_side_bias": request.vwap_side_bias,
        "vwap_max_distance_bps": request.vwap_max_distance_bps,
        "vwap_min_slope_bps": request.vwap_min_slope_bps,
        "session_filter": request.session_filter or "none",
        "cost_filter": request.cost_filter or "none",
        "max_execution_cost_r": request.max_execution_cost_r,
        "min_samples": settings.intraday_research_min_samples,
        "min_effective_samples": settings.intraday_research_min_effective_samples,
        "min_symbols": settings.intraday_research_min_symbols,
        "min_years": settings.intraday_research_min_years,
        "universe_file": settings.intraday_universe_file,
        "symbols": request.symbols,
    }


def _discovery_params_match(stored: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(stored.get(key) == value for key, value in expected.items())


def _completed_equivalent_discovery_run(db, expected: dict[str, Any]) -> DiscoveryRun | None:  # noqa: ANN001
    return (
        db.query(DiscoveryRun)
        .filter(DiscoveryRun.status == "completed")
        .filter(DiscoveryRun.params_json.contains(expected))
        .order_by(DiscoveryRun.started_at.desc())
        .first()
    )


def _intraday_research_vwap_condition() -> str:
    return (os.environ.get("TRADEO_INTRADAY_RESEARCH_VWAP_CONDITION") or "none").strip().lower() or "none"


def _intraday_research_context_filter_spec():
    return normalize_context_filter_spec(
        session_filter=os.environ.get("TRADEO_INTRADAY_RESEARCH_SESSION_FILTER"),
        cost_filter=os.environ.get("TRADEO_INTRADAY_RESEARCH_COST_FILTER"),
        max_execution_cost_r=os.environ.get("TRADEO_INTRADAY_RESEARCH_MAX_EXECUTION_COST_R"),
    )


def _optional_env(key: str) -> str | None:
    value = os.environ.get(key)
    return value.strip().lower() if value and value.strip() else None


def _optional_float_env(key: str) -> float | None:
    value = os.environ.get(key)
    if value is None or not value.strip():
        return None
    return float(value)


def _intraday_research_parallel_symbol_chunks(settings: Settings) -> int:
    return max(1, int(settings.intraday_research_parallel_symbol_chunks or 1))


def _intraday_research_process_chunk_count(settings: Settings) -> int:
    configured = _intraday_research_parallel_symbol_chunks(settings)
    if not bool(settings.intraday_research_process_pool_enabled):
        return configured
    if not _intraday_research_adaptive_chunks_enabled():
        return configured
    timeframe_count = len(settings.intraday_timeframe_list)
    if timeframe_count <= 0:
        return configured
    process_workers = max(1, int(settings.intraday_research_process_workers or 1))
    symbol_limit = int(settings.intraday_research_limit_default or 0)
    if configured < 5 or process_workers <= 1 or symbol_limit <= configured:
        return configured

    candidate = configured + 1
    current_jobs = configured * timeframe_count
    candidate_jobs = candidate * timeframe_count
    if current_jobs == process_workers and candidate_jobs > current_jobs:
        return min(candidate, symbol_limit)
    if current_jobs % process_workers != 0 and candidate_jobs % process_workers == 0:
        return min(candidate, symbol_limit)
    return configured


def _intraday_research_adaptive_chunks_enabled() -> bool:
    return _intraday_env_flag_enabled(_INTRADAY_RESEARCH_ADAPTIVE_CHUNKS_ENV)


def _intraday_env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _intraday_research_process_symbol_chunks(
    settings: Settings,
    timeframe: str,
    chunk_count: int,
) -> list[tuple[int, tuple[str, ...], int]]:
    chunk_count = max(1, int(chunk_count))
    symbols = pick_symbols(
        limit=settings.intraday_research_limit_default,
        interval=timeframe,
        universe_file=universe_file_for_interval(settings, timeframe),
    )
    cost_estimates = _intraday_research_symbol_cost_estimates(settings, timeframe, symbols)
    if len(cost_estimates) == len(symbols):
        return _intraday_research_cost_balanced_symbol_chunks(
            symbols,
            cost_estimates,
            chunk_count,
        )
    chunks: list[list[str]] = [[] for _ in range(chunk_count)]
    for position, symbol in enumerate(symbols):
        chunks[position % chunk_count].append(symbol)
    return [
        (chunk_index, tuple(chunk_symbols), len(chunk_symbols))
        for chunk_index, chunk_symbols in enumerate(chunks)
    ]


def _intraday_research_cost_balanced_symbol_chunks(
    symbols: list[str],
    cost_estimates: dict[str, int],
    chunk_count: int,
) -> list[tuple[int, tuple[str, ...], int]]:
    chunks: list[list[str]] = [[] for _ in range(chunk_count)]
    chunk_costs = [0 for _ in range(chunk_count)]
    ranked_symbols = sorted(
        enumerate(symbols),
        key=lambda item: (-int(cost_estimates[item[1].upper()]), item[0]),
    )
    for _, symbol in ranked_symbols:
        target_index = min(
            range(chunk_count),
            key=lambda index: (chunk_costs[index], len(chunks[index]), index),
        )
        chunks[target_index].append(symbol)
        chunk_costs[target_index] += int(cost_estimates[symbol.upper()])
    return [
        (chunk_index, tuple(chunk_symbols), int(chunk_costs[chunk_index]))
        for chunk_index, chunk_symbols in enumerate(chunks)
    ]


def _intraday_research_symbol_cost_estimates(
    settings: Settings,
    timeframe: str,
    symbols: list[str],
) -> dict[str, int]:
    if not symbols or not bool(settings.market_data_cache_enabled):
        return {}
    try:
        cache_path = settings.market_data_cache_path
    except OSError:
        return {}

    estimates: dict[str, int] = {}
    period = str(settings.intraday_research_period)
    for symbol in symbols:
        metadata_path = cache_path / (
            "_".join(
                _intraday_market_data_cache_safe_part(part)
                for part in (symbol.upper(), timeframe, period)
            )
            + ".metadata.json"
        )
        payload = _intraday_research_read_json(metadata_path)
        if (
            str(payload.get("symbol") or "").upper() != symbol.upper()
            or str(payload.get("period") or "") != period
            or str(payload.get("interval") or "") != str(timeframe)
        ):
            continue
        try:
            rows = int(payload.get("rows") or 0)
        except (TypeError, ValueError):
            continue
        estimates[symbol.upper()] = _intraday_research_window_cost_estimate(settings, rows)
    return estimates


def _intraday_research_window_cost_estimate(settings: Settings, rows: int) -> int:
    rows = max(0, int(rows))
    window_sizes = sorted(
        {int(size) for size in settings.intraday_research_window_size_list if int(size) >= 10}
    )
    forward_bars = sorted(
        {int(forward) for forward in settings.intraday_research_forward_bar_list if int(forward) > 0}
    )
    max_windows_per_symbol = max(0, int(settings.intraday_research_max_windows_per_symbol or 0))
    if not window_sizes or not forward_bars or max_windows_per_symbol == 0:
        return 0
    max_forward = max(forward_bars)
    if rows < max(window_sizes) + max_forward + 5:
        return 0

    stride = max(1, int(settings.intraday_research_stride or 1))
    base_quota = max_windows_per_symbol // len(window_sizes)
    quota_remainder = max_windows_per_symbol - base_quota * len(window_sizes)
    estimate = 0
    for index, window_size in enumerate(window_sizes):
        if rows < window_size + max_forward + 2:
            continue
        quota = base_quota + (1 if index < quota_remainder else 0)
        positions = len(range(window_size - 1, rows - max_forward - 1, stride))
        estimate += min(max(positions, 0), quota)
    return min(max_windows_per_symbol, estimate)


def _intraday_market_data_cache_safe_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "."} else "_" for ch in value).strip("._")


def _intraday_research_read_json(path: Any) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _intraday_research_symbols_for_chunk(
    settings: Settings,
    timeframe: str,
    symbol_chunk: tuple[int, int] | None,
) -> list[str] | None:
    if symbol_chunk is None:
        return None
    chunk_index, chunk_count = symbol_chunk
    chunk_count = max(1, int(chunk_count))
    chunk_index = max(0, min(int(chunk_index), chunk_count - 1))
    symbols = pick_symbols(
        limit=settings.intraday_research_limit_default,
        interval=timeframe,
        universe_file=universe_file_for_interval(settings, timeframe),
    )
    return [symbol for pos, symbol in enumerate(symbols) if pos % chunk_count == chunk_index]


def _intraday_chunk_details(
    symbol_chunk: tuple[int, int] | None,
    symbols: list[str] | None,
) -> dict[str, Any] | None:
    if symbol_chunk is None:
        return None
    chunk_index, chunk_count = symbol_chunk
    return {
        "index": int(chunk_index),
        "number": int(chunk_index) + 1,
        "count": int(chunk_count),
        "symbols": len(symbols) if symbols is not None else None,
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
        seconds_attr="intraday_research_interval_seconds",
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
        register_daily_paper_jobs(scheduler, settings)
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
