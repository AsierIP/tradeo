from __future__ import annotations

import csv
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tradeo.research_capacity.capacity_001.v1"
REQUIRED_METRIC_FIELDS = [
    "experiment_id",
    "runner_name",
    "research_family",
    "universe_policy",
    "symbols_count",
    "timeframe",
    "window",
    "forward_set",
    "cache_mode",
    "started_at",
    "finished_at",
    "elapsed_seconds",
    "windows_processed",
    "clusters_processed",
    "candidates_total",
    "candidates_accepted",
    "candidates_rejected",
    "near_misses",
    "rejected_persisted",
    "store_rejected_enabled",
    "cache_hit_rate",
    "data_missing_count",
    "blocker_counts",
    "fdr_fail_count",
    "wrc_fail_count",
    "spa_fail_count",
    "cost_x2_fail_count",
    "oos_fail_count",
    "drawdown_fail_count",
    "placebo_fail_count",
    "artifact_bytes",
    "cpu_seconds",
    "memory_peak_mb",
    "decision",
    "safety_flags",
]
SAFETY_FLAGS = {
    "cache_only": True,
    "dry_run": True,
    "no_ibkr": True,
    "no_orders": True,
    "no_signals": True,
    "no_preview": True,
    "no_candidate_approval": True,
    "no_downloads": True,
}
RESEARCH_SURFACE_ROWS = [
    {
        "path": "scripts/run_daily_gap_matrix_dry_run.py",
        "surface": "GAP dry-run matrix",
        "family": "gap",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Safe parser/matrix baseline for capacity microbench.",
    },
    {
        "path": "scripts/run_daily_gap_confirmatory_matrix.py",
        "surface": "GAP confirmatory matrix",
        "family": "gap",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Research matrix only; candidate approval remains outside CAPACITY-001.",
    },
    {
        "path": "backend/tradeo/modules/daily_swing/gap_backtest_matrix.py",
        "surface": "GAP backtest matrix module",
        "family": "gap",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Backtest matrix implementation; must keep no-lookahead/cost gates.",
    },
    {
        "path": "scripts/validate_daily_gap_backtest_matrix.py",
        "surface": "GAP matrix validation",
        "family": "gap",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Validation-only surface.",
    },
    {
        "path": "scripts/backtest_daily_swing_dss_pb_001.py",
        "surface": "Daily PB research runner",
        "family": "daily",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Historical rejected family; not a rescue lane for CAPACITY-001.",
    },
    {
        "path": "scripts/backtest_daily_swing_dss_bo_001.py",
        "surface": "Daily BO research runner",
        "family": "daily",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Historical rejected family; not a rescue lane for CAPACITY-001.",
    },
    {
        "path": "scripts/backtest_daily_swing_dss_co_001.py",
        "surface": "Daily CO research runner",
        "family": "daily",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Historical rejected family; not a rescue lane for CAPACITY-001.",
    },
    {
        "path": "scripts/backtest_daily_swing_dss_cw_001.py",
        "surface": "Daily CW research runner",
        "family": "daily",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Historical rejected family; not a rescue lane for CAPACITY-001.",
    },
    {
        "path": "scripts/run_intraday_research_wave.py",
        "surface": "Intraday wave runner",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Heavy research runner; blocked from productive execution in CAPACITY-001.",
    },
    {
        "path": "scripts/plan_intraday_research_next.py",
        "surface": "Intraday planner",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Planning-only surface for experiment queue design.",
    },
    {
        "path": "scripts/check_intraday_research_readiness.py",
        "surface": "Intraday readiness",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Readiness check; safe for baseline diagnostics.",
    },
    {
        "path": "scripts/diagnose_intraday_pattern_funnel.py",
        "surface": "Intraday funnel diagnostics",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Rejected/blocker diagnostics.",
    },
    {
        "path": "scripts/analyze_intraday_research_forensics.py",
        "surface": "Intraday forensics",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Rejected/near-miss mining input.",
    },
    {
        "path": "backend/tradeo/modules/intraday/research_validation_stack.py",
        "surface": "Intraday validation stack",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "FDR/WRC/SPA-light, OOS, cost and blocker validation surface.",
    },
    {
        "path": "scripts/run_vwap_shadow_once.py",
        "surface": "VWAP shadow once",
        "family": "laboratory",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": True,
        "can_generate_preview_or_orders": False,
        "notes": "Explicitly excluded from CAPACITY-001.",
    },
    {
        "path": "scripts/run_lab_shadow_scheduled_once.sh",
        "surface": "Scheduled lab shadow",
        "family": "laboratory",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": True,
        "can_generate_preview_or_orders": False,
        "notes": "Explicitly excluded from CAPACITY-001.",
    },
    {
        "path": "scripts/fetch_ibkr_intraday_candidates.py",
        "surface": "IBKR candidate fetch",
        "family": "data",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": True,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "IBKR path; blocked for CAPACITY-001.",
    },
    {
        "path": "scripts/notify_tradeo_orders.sh",
        "surface": "Order notification",
        "family": "execution",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": True,
        "notes": "Execution-adjacent; blocked for CAPACITY-001.",
    },
    {
        "path": "backend/tradeo/routers/research.py",
        "surface": "Research API/core",
        "family": "research_api",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Broker-safe but may write DB/artifacts; not used by CAPACITY-001 microbench.",
    },
    {
        "path": "backend/tradeo/tasks/worker.py",
        "surface": "Intraday background research worker",
        "family": "intraday",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Background DB write path; excluded from CAPACITY-001.",
    },
    {
        "path": "backend/tradeo/research/quant_validation.py",
        "surface": "Quant validation FDR/WRC/SPA gates",
        "family": "validation",
        "research_only": True,
        "dry_run_capable": True,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Validation gates used by research scoring.",
    },
    {
        "path": "backend/tradeo/research/novel_pattern_registry.py",
        "surface": "Rejected/near-miss persistence",
        "family": "forensics",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": True,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "DB persistence surface; CAPACITY-001 reads artifacts only.",
    },
    {
        "path": "scripts/warm_intraday_cache_resilient.py",
        "surface": "Intraday cache warming",
        "family": "data",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": True,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Read-only market data path but requires IBKR/downloads; blocked for CAPACITY-001.",
    },
    {
        "path": "scripts/cache_daily_ohlcv.py",
        "surface": "Daily cache fill",
        "family": "data",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": True,
        "can_generate_candidates": False,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Read-only market data path but requires IBKR/downloads; blocked for CAPACITY-001.",
    },
    {
        "path": "backend/tradeo/routers/backtests.py",
        "surface": "Backtest API",
        "family": "backtest_api",
        "research_only": True,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": True,
        "can_generate_signals": False,
        "can_generate_preview_or_orders": False,
        "notes": "Provider may refresh data; excluded from CAPACITY-001 microbench.",
    },
    {
        "path": "backend/tradeo/routers/laboratory.py",
        "surface": "Laboratory scanner API",
        "family": "laboratory",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": False,
        "can_generate_candidates": False,
        "can_generate_signals": True,
        "can_generate_preview_or_orders": True,
        "notes": "Execution perimeter; blocked for CAPACITY-001.",
    },
    {
        "path": "backend/tradeo/routers/signals.py",
        "surface": "Signals API",
        "family": "execution",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": True,
        "can_generate_candidates": False,
        "can_generate_signals": True,
        "can_generate_preview_or_orders": True,
        "notes": "Execution perimeter; blocked for CAPACITY-001.",
    },
    {
        "path": "backend/tradeo/routers/ibkr.py",
        "surface": "IBKR API",
        "family": "execution",
        "research_only": False,
        "dry_run_capable": False,
        "cache_only_capable": False,
        "ibkr_required": True,
        "can_generate_candidates": False,
        "can_generate_signals": True,
        "can_generate_preview_or_orders": True,
        "notes": "Broker/API perimeter; blocked for CAPACITY-001.",
    },
]


class ResearchCapacityError(ValueError):
    decision = "RESEARCH_CAPACITY_ERROR"


class ResearchCapacitySafetyError(ResearchCapacityError):
    decision = "RESEARCH_CAPACITY_SAFETY_BLOCKED"


@dataclass(frozen=True)
class CapacityRunConfig:
    repo_root: Path
    runtime_root: Path
    output_dir: Path
    research_dir: Path
    max_workload: int
    cache_only: bool
    dry_run: bool
    no_ibkr: bool
    no_orders: bool
    no_signals: bool
    no_preview: bool
    no_candidate_approval: bool
    no_downloads: bool


def enforce_capacity_guards(config: CapacityRunConfig) -> None:
    if not config.cache_only:
        raise ResearchCapacitySafetyError("CAPACITY-001 requires cache-only mode.")
    if not config.dry_run:
        raise ResearchCapacitySafetyError("CAPACITY-001 requires dry-run mode.")
    if not config.no_downloads:
        raise ResearchCapacitySafetyError("CAPACITY-001 refuses downloads.")
    if not config.no_ibkr:
        raise ResearchCapacitySafetyError("CAPACITY-001 refuses IBKR access.")
    if not config.no_orders:
        raise ResearchCapacitySafetyError("CAPACITY-001 refuses order paths.")
    if not config.no_signals:
        raise ResearchCapacitySafetyError("CAPACITY-001 refuses signal outputs.")
    if not config.no_preview:
        raise ResearchCapacitySafetyError("CAPACITY-001 refuses preview outputs.")
    if not config.no_candidate_approval:
        raise ResearchCapacitySafetyError("CAPACITY-001 refuses candidate approval.")
    if config.max_workload < 1 or config.max_workload > 1000:
        raise ResearchCapacitySafetyError("CAPACITY-001 max workload must be between 1 and 1000.")


def metric_schema() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "required_fields": REQUIRED_METRIC_FIELDS,
        "field_count": len(REQUIRED_METRIC_FIELDS),
        "types": {
            "elapsed_seconds": "number",
            "cache_hit_rate": "number",
            "blocker_counts": "object<string,int>",
            "safety_flags": "object<string,bool>",
        },
        "safety_invariants": SAFETY_FLAGS,
    }


def research_surface_rows() -> list[dict[str, Any]]:
    rows = []
    for row in RESEARCH_SURFACE_ROWS:
        item = dict(row)
        blocked_reasons = []
        if item["ibkr_required"]:
            blocked_reasons.append("ibkr_required")
        if item["can_generate_signals"]:
            blocked_reasons.append("can_generate_signals")
        if item["can_generate_preview_or_orders"]:
            blocked_reasons.append("can_generate_preview_or_orders")
        if not item["research_only"]:
            blocked_reasons.append("not_research_only")
        if not item["cache_only_capable"]:
            blocked_reasons.append("not_cache_only_capable")
        item["blocked_for_capacity_001"] = bool(blocked_reasons)
        item["capacity_001_blockers"] = ",".join(blocked_reasons)
        rows.append(item)
    return rows


def collect_research_surface(repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    research = repo_root / "research"
    modules = repo_root / "backend" / "tradeo" / "modules"
    scripts = repo_root / "scripts"
    ohlcv_cache = runtime_root / "ohlcv_cache"
    cache_files = list(ohlcv_cache.glob("*.csv")) if ohlcv_cache.exists() else []
    timeframes = Counter(_cache_timeframe(path) for path in cache_files)
    return {
        "daily_swing_modules": sorted(path.stem for path in (modules / "daily_swing").glob("*.py")),
        "intraday_modules": sorted(path.stem for path in (modules / "intraday").glob("*.py")),
        "research_docs": len(list(research.rglob("*.md"))) if research.exists() else 0,
        "gap_reports": len(list((research / "daily_swing" / "gap").glob("DSS_GAP_*.md"))),
        "intraday_scripts": sorted(path.name for path in scripts.glob("*intraday*.py")),
        "daily_scripts": sorted(path.name for path in scripts.glob("*daily*.py")),
        "cache_files": len(cache_files),
        "cache_timeframes": dict(sorted(timeframes.items())),
        "surface_rows": research_surface_rows(),
        "surface_row_count": len(RESEARCH_SURFACE_ROWS),
        "runtime_root": str(runtime_root),
    }


def run_capacity_microbench(config: CapacityRunConfig) -> dict[str, Any]:
    enforce_capacity_guards(config)
    started = _now()
    t0 = time.perf_counter()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.research_dir.mkdir(parents=True, exist_ok=True)

    cache_files = sorted((config.runtime_root / "ohlcv_cache").glob("*.csv")) if (config.runtime_root / "ohlcv_cache").exists() else []
    sampled = cache_files[: config.max_workload]
    rows_seen = 0
    bytes_seen = 0
    symbols: set[str] = set()
    timeframes: Counter[str] = Counter()
    for path in sampled:
        bytes_seen += path.stat().st_size
        symbols.add(_cache_symbol(path))
        timeframes[_cache_timeframe(path)] += 1
        with path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle)
            rows_seen += max(sum(1 for _ in reader) - 1, 0)

    gap_matrix = config.repo_root / "research" / "daily_swing" / "gap" / "dss_gap_003_backtest_matrix.json"
    matrix_rows = _json_len(gap_matrix)
    runtime_jsons = list(config.runtime_root.glob("*.json")) if config.runtime_root.exists() else []
    rejected, near_misses, blockers = _scan_prior_artifacts(config.repo_root, config.runtime_root)
    elapsed = time.perf_counter() - t0
    data_available = bool(sampled)
    decision = "RESEARCH_CAPACITY_BASELINE_READY" if data_available else "RESEARCH_CAPACITY_BLOCKED_BY_CACHE"
    finished = _now()

    metrics = [
        _metric(
            experiment_id="CAPACITY-001-GAP-DRY-RUN-PARSER",
            runner_name="gap_matrix_parser_capacity",
            research_family="daily_gap",
            universe_policy="existing_gap_matrix",
            symbols_count=0,
            timeframe="1d",
            window="pre_registered_gap_matrix",
            forward_set="same_day,next_day",
            started_at=started,
            finished_at=finished,
            elapsed_seconds=elapsed,
            windows_processed=matrix_rows,
            clusters_processed=0,
            artifact_bytes=gap_matrix.stat().st_size if gap_matrix.exists() else 0,
            decision="READY" if matrix_rows else "DATA_NOT_AVAILABLE",
        ),
        _metric(
            experiment_id="CAPACITY-001-INTRADAY-CACHE-PARSE",
            runner_name="intraday_cache_parse_microbench",
            research_family="intraday",
            universe_policy="cached_ohlcv_sample",
            symbols_count=len(symbols),
            timeframe=",".join(sorted(timeframes)) or "NA",
            window=f"max_files={config.max_workload}",
            forward_set="diagnostic_only",
            started_at=started,
            finished_at=finished,
            elapsed_seconds=elapsed,
            windows_processed=rows_seen,
            clusters_processed=len(sampled),
            artifact_bytes=bytes_seen,
            cache_hit_rate=1.0 if sampled else 0.0,
            data_missing_count=0 if sampled else 1,
            blocker_counts={} if sampled else {"cache_missing": 1},
            decision="READY" if sampled else "DATA_NOT_AVAILABLE",
        ),
        _metric(
            experiment_id="CAPACITY-001-REJECTED-NEAR-MISS-PARSE",
            runner_name="artifact_text_counter",
            research_family="cross_research",
            universe_policy="existing_artifacts_only",
            symbols_count=0,
            timeframe="mixed",
            window=f"json_files={len(runtime_jsons)}",
            forward_set="diagnostic_only",
            started_at=started,
            finished_at=finished,
            elapsed_seconds=elapsed,
            windows_processed=len(runtime_jsons),
            clusters_processed=0,
            candidates_rejected=rejected,
            near_misses=near_misses,
            rejected_persisted=rejected > 0,
            store_rejected_enabled=rejected > 0,
            artifact_bytes=sum(path.stat().st_size for path in runtime_jsons[: config.max_workload]),
            blocker_counts=blockers,
            decision="READY",
        ),
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "started_at": started,
        "finished_at": finished,
        "elapsed_seconds": round(elapsed, 6),
        "runtime_root": str(config.runtime_root),
        "max_workload": config.max_workload,
        "cache_files_sampled": len(sampled),
        "cache_files_available": len(cache_files),
        "rows_seen": rows_seen,
        "surface_inventory": collect_research_surface(config.repo_root, config.runtime_root),
        "metrics": metrics,
        "safety_flags": dict(SAFETY_FLAGS),
    }
    json_path = config.output_dir / "capacity_001_microbench_results.json"
    csv_path = config.output_dir / "capacity_001_microbench_results.csv"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_metrics_csv(csv_path, metrics)
    payload["runtime_paths"] = {"json": str(json_path), "csv": str(csv_path)}
    return payload


def run_capacity_plan(config: CapacityRunConfig) -> dict[str, Any]:
    enforce_capacity_guards(config)
    started = _now()
    t0 = time.perf_counter()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.research_dir.mkdir(parents=True, exist_ok=True)

    cache_rows = _collect_cache_rows(config.runtime_root / "ohlcv_cache")
    universe = _read_universe(config.runtime_root)
    rc002_a = _intraday_cache_readiness(universe, cache_rows)
    rc002_b = _intraday_matrix_plan(universe, cache_rows, config.repo_root)
    rc002_c = _rejected_mining(config.runtime_root)
    throughput = _capacity_002_throughput(rc002_a, rc002_b, rc002_c, started, time.perf_counter() - t0)
    decision = _capacity_002_decision(rc002_a, rc002_b, rc002_c)
    finished = _now()
    payload = {
        "schema_version": "tradeo.research_capacity.capacity_002.v1",
        "task_id": "T-RESEARCH-CAPACITY-002",
        "decision": decision,
        "started_at": started,
        "finished_at": finished,
        "elapsed_seconds": round(time.perf_counter() - t0, 6),
        "runtime_root": str(config.runtime_root),
        "experiments_executed": ["RC-002-A", "RC-002-B", "RC-002-C"],
        "experiments_not_executed": ["GAP next-day redesign", "ETF/macro", "new Daily line", "paper/shadow promotion"],
        "rc_002_a": rc002_a,
        "rc_002_b": rc002_b,
        "rc_002_c": rc002_c,
        "throughput": throughput,
        "safety_flags": dict(SAFETY_FLAGS),
    }
    json_path = config.output_dir / "capacity_002_results.json"
    csv_path = config.output_dir / "capacity_002_metrics.csv"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_dicts_csv(csv_path, throughput["metrics"])
    payload["runtime_paths"] = {"json": str(json_path), "csv": str(csv_path)}
    payload["versioned_docs"] = write_capacity_002_docs(config.repo_root, payload)
    return payload


def write_capacity_002_docs(repo_root: Path, payload: dict[str, Any]) -> dict[str, str]:
    out = repo_root / "research" / "capacity"
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "a_md": out / "CAPACITY_002_A_INTRADAY_CACHE_READINESS.md",
        "a_csv": out / "capacity_002_a_intraday_cache_readiness.csv",
        "a_json": out / "capacity_002_a_intraday_cache_readiness.json",
        "b_md": out / "CAPACITY_002_B_INTRADAY_MATRIX_PLAN.md",
        "b_csv": out / "capacity_002_b_intraday_matrix_plan.csv",
        "b_json": out / "capacity_002_b_intraday_matrix_plan.json",
        "c_md": out / "CAPACITY_002_C_REJECTED_MINING.md",
        "c_csv": out / "capacity_002_c_rejected_mining.csv",
        "c_json": out / "capacity_002_c_rejected_mining.json",
        "throughput_md": out / "CAPACITY_002_THROUGHPUT_SUMMARY.md",
        "throughput_csv": out / "capacity_002_throughput_summary.csv",
        "throughput_json": out / "capacity_002_throughput_summary.json",
        "final_md": out / "CAPACITY_002_FINAL_REPORT.md",
        "decision_json": out / "CAPACITY_002_DECISION.json",
    }
    a = payload["rc_002_a"]
    b = payload["rc_002_b"]
    c = payload["rc_002_c"]
    throughput = payload["throughput"]
    decision = {
        "schema_version": payload["schema_version"],
        "task_id": payload["task_id"],
        "decision": payload["decision"],
        "ready_for_batch": payload["decision"] == "RESEARCH_CAPACITY_PLAN_EXECUTED_READY_FOR_BATCH",
        "partial_decisions": {
            "RC-002-A": a["decision"],
            "RC-002-B": b["decision"],
            "RC-002-C": c["decision"],
        },
        "recommended_next_batch": throughput["recommended_next_batch"],
        "safety_flags": dict(SAFETY_FLAGS),
    }
    paths["a_json"].write_text(json.dumps(a, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["b_json"].write_text(json.dumps(b, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["c_json"].write_text(json.dumps(c, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["throughput_json"].write_text(json.dumps(throughput, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["decision_json"].write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_dicts_csv(paths["a_csv"], a["timeframe_rows"])
    _write_dicts_csv(paths["b_csv"], b["matrix_rows"])
    _write_dicts_csv(paths["c_csv"], c["blocker_rows"])
    _write_dicts_csv(paths["throughput_csv"], throughput["metrics"])
    paths["a_md"].write_text(_capacity_002_a_markdown(a), encoding="utf-8")
    paths["b_md"].write_text(_capacity_002_b_markdown(b), encoding="utf-8")
    paths["c_md"].write_text(_capacity_002_c_markdown(c), encoding="utf-8")
    paths["throughput_md"].write_text(_capacity_002_throughput_markdown(throughput), encoding="utf-8")
    paths["final_md"].write_text(_capacity_002_final_report(payload, decision), encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def build_experiment_queue() -> list[dict[str, Any]]:
    rows = [
        ("RC-002-A", 1, 95, "Intraday universe/cache expansion readiness", "High", "Existing intraday cache + universe manifests", "30m/60d cache", "short", "Lowest leakage risk and directly removes current universe/cache uncertainty.", False),
        ("RC-002-B", 2, 88, "Intraday 15m/30m/1h search-space matrix", "High", "Cached OHLCV by timeframe", "15m,30m,1h cache", "medium", "High falsification value once cache coverage is known.", True),
        ("RC-002-C", 3, 76, "Regime-conditioned intraday search", "Medium", "Cached intraday features and SPY/QQQ context", "intraday + benchmark cache", "medium", "Useful after baseline matrix; adds leakage/regime complexity.", True),
        ("RC-002-D", 4, 70, "Daily new search-space, excluding PB/BO/CO/CW/GAP rescue", "Medium", "Daily OHLCV cache", "1d cache", "medium", "Separate daily lane without rescuing rejected families.", True),
        ("RC-002-E", 5, 55, "GAP next-day only redesign", "Low", "Prior GAP ledgers", "gap ledger cache", "short", "Low EVI but cheap protocol design; execution remains blocked pending Director.", True),
        ("RC-002-F", 6, 50, "ETF/macro separate etf_macro research lane", "Medium", "ETF/macro cache", "separate ETF cache", "medium", "Medium EVI but intentionally lower priority because it is a separate lane and must not mix with stock_only.", True),
    ]
    return [
        {
            "experiment_id": item[0],
            "priority": item[1],
            "priority_score": item[2],
            "name": item[3],
            "expected_value_of_information": item[4],
            "data_required": item[5],
            "cache_required": item[6],
            "estimated_runtime": item[7],
            "priority_rationale": item[8],
            "safety_requirements": "cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false",
            "gates_required": "no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo",
            "success_metrics": "falsifiable OOS metric, cache coverage, elapsed_seconds, blockers",
            "blocker_conditions": "missing cache, leakage risk, insufficient sample, failed safety guard",
            "needs_director_approval": item[9],
        }
        for item in rows
    ]


def write_capacity_docs(
    repo_root: Path,
    microbench: dict[str, Any],
    research_dir: Path | None = None,
) -> dict[str, str]:
    out = research_dir or repo_root / "research" / "capacity"
    out.mkdir(parents=True, exist_ok=True)
    schema = metric_schema()
    queue = build_experiment_queue()
    inventory = microbench["surface_inventory"]
    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "T-RESEARCH-CAPACITY-001",
        "decision": microbench["decision"],
        "ready": microbench["decision"] == "RESEARCH_CAPACITY_BASELINE_READY",
        "allowed_experiments_after_director_authorizes_capacity_002": [
            row["experiment_id"] for row in queue if not row["needs_director_approval"]
        ],
        "requires_director_approval": [
            row["experiment_id"] for row in queue if row["needs_director_approval"]
        ],
        "live_allowed": False,
        "paper_allowed": False,
        "orders_allowed": False,
        "order_code_changed": False,
        "gates_relaxed": False,
        "next_task": "T-RESEARCH-CAPACITY-002 - Execute prioritized cache-only capacity plan, no candidate approval"
        if microbench["decision"] == "RESEARCH_CAPACITY_BASELINE_READY"
        else None,
        "safety_flags": dict(SAFETY_FLAGS),
    }
    paths = {
        "schema_md": out / "CAPACITY_001_METRICS_SCHEMA.md",
        "microbench_md": out / "CAPACITY_001_MICROBENCH_SUMMARY.md",
        "microbench_csv": out / "capacity_001_microbench_summary.csv",
        "inventory_md": out / "CAPACITY_001_RESEARCH_SURFACE_INVENTORY.md",
        "inventory_csv": out / "capacity_001_research_surface_inventory.csv",
        "inventory_json": out / "capacity_001_research_surface_inventory.json",
        "queue_md": out / "CAPACITY_001_EXPERIMENT_QUEUE.md",
        "queue_csv": out / "capacity_001_experiment_queue.csv",
        "queue_json": out / "capacity_001_experiment_queue.json",
        "final_md": out / "CAPACITY_001_FINAL_REPORT.md",
        "decision_json": out / "CAPACITY_001_DECISION.json",
    }
    paths["schema_md"].write_text(_schema_markdown(schema), encoding="utf-8")
    paths["inventory_md"].write_text(_inventory_markdown(inventory), encoding="utf-8")
    paths["inventory_json"].write_text(json.dumps(inventory["surface_rows"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_dicts_csv(paths["inventory_csv"], inventory["surface_rows"])
    paths["microbench_md"].write_text(_microbench_markdown(microbench), encoding="utf-8")
    _write_metrics_csv(paths["microbench_csv"], microbench["metrics"])
    paths["queue_md"].write_text(_queue_markdown(queue), encoding="utf-8")
    _write_dicts_csv(paths["queue_csv"], queue)
    paths["queue_json"].write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["decision_json"].write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["final_md"].write_text(_final_report(decision, inventory, microbench, queue), encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def _metric(**overrides: Any) -> dict[str, Any]:
    base = {
        "experiment_id": "",
        "runner_name": "",
        "research_family": "",
        "universe_policy": "",
        "symbols_count": 0,
        "timeframe": "",
        "window": "",
        "forward_set": "",
        "cache_mode": "cache_only",
        "started_at": "",
        "finished_at": "",
        "elapsed_seconds": 0.0,
        "windows_processed": 0,
        "clusters_processed": 0,
        "candidates_total": 0,
        "candidates_accepted": 0,
        "candidates_rejected": 0,
        "near_misses": 0,
        "rejected_persisted": False,
        "store_rejected_enabled": False,
        "cache_hit_rate": 1.0,
        "data_missing_count": 0,
        "blocker_counts": {},
        "fdr_fail_count": 0,
        "wrc_fail_count": 0,
        "spa_fail_count": 0,
        "cost_x2_fail_count": 0,
        "oos_fail_count": 0,
        "drawdown_fail_count": 0,
        "placebo_fail_count": 0,
        "artifact_bytes": 0,
        "cpu_seconds": None,
        "memory_peak_mb": None,
        "decision": "",
        "safety_flags": dict(SAFETY_FLAGS),
    }
    base.update(overrides)
    return base


def _write_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_dicts_csv(path, rows, fieldnames=REQUIRED_METRIC_FIELDS)


def _write_dicts_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fieldnames or (list(rows[0]) if rows else ["empty"])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def _json_len(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else len(data.get("rows", [])) if isinstance(data, dict) else 0


def _scan_prior_artifacts(repo_root: Path, runtime_root: Path) -> tuple[int, int, dict[str, int]]:
    rejected = 0
    near_misses = 0
    blockers: Counter[str] = Counter()
    paths = list((repo_root / "research").rglob("*.md"))[:300]
    if runtime_root.exists():
        paths.extend(list(runtime_root.glob("*.json"))[:300])
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        rejected += text.count("rejected") + text.count("rechaz")
        near_misses += text.count("near_miss") + text.count("near-miss")
        for token in ("fdr", "wrc", "spa", "cost_x2", "oos", "drawdown", "placebo", "cache"):
            if token in text:
                blockers[token] += 1
    return rejected, near_misses, dict(blockers)


def _collect_cache_rows(cache_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
    rows: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    if not cache_dir.exists():
        return {}
    for path in sorted(cache_dir.glob("*.csv")):
        symbol = _cache_symbol(path)
        timeframe = _cache_timeframe(path)
        count = 0
        first_ts = ""
        last_ts = ""
        with path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.DictReader(handle)
            for idx, row in enumerate(reader):
                if idx == 0:
                    first_ts = row.get("date") or row.get("timestamp") or ""
                last_ts = row.get("date") or row.get("timestamp") or ""
                count += 1
        rows[timeframe][symbol] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "rows": count,
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
            "bytes": path.stat().st_size,
        }
    return {key: dict(value) for key, value in rows.items()}


def _read_universe(runtime_root: Path) -> dict[str, Any]:
    metadata_path = _first_existing(
        runtime_root,
        [
            "universe_intraday_stock_only_v3.metadata.json",
            "universe_intraday_stock_only_v2.metadata.json",
            "universe_intraday_stock_only.metadata.json",
        ],
    )
    csv_path = _first_existing(
        runtime_root,
        [
            "universe_intraday_stock_only_v3.csv",
            "universe_intraday_stock_only_v2.csv",
            "universe_intraday_stock_only.csv",
        ],
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path else {}
    rows = _read_csv_rows(csv_path) if csv_path else []
    selected_rows = [row for row in rows if str(row.get("selected", "")).lower() == "true"]
    selected_symbols = metadata.get("selected_symbols") or [row.get("symbol", "") for row in selected_rows]
    product_classes = Counter(row.get("product_class", "unknown") or "unknown" for row in selected_rows)
    suspicious_selected = [
        row.get("symbol", "")
        for row in selected_rows
        if row.get("product_class") not in ("common_stock", "adr", "unknown", "")
        or _meaningful_cell(row.get("product_flags"), allowed={"adr"})
        or _meaningful_cell(row.get("product_rejection_reason"))
    ]
    return {
        "metadata_path": str(metadata_path) if metadata_path else None,
        "csv_path": str(csv_path) if csv_path else None,
        "selected_symbols": sorted(set(symbol for symbol in selected_symbols if symbol)),
        "selected_count": int(metadata.get("selected_count") or len(selected_symbols)),
        "total_candidates": int(metadata.get("total_candidates") or len(rows)),
        "rejected_count": int(metadata.get("rejected_count") or 0),
        "product_policy": metadata.get("product_policy", "unknown"),
        "product_class_distribution": dict(sorted(product_classes.items())),
        "suspicious_selected_count": len(suspicious_selected),
        "suspicious_selected_symbols": sorted(symbol for symbol in suspicious_selected if symbol)[:25],
        "reason_counts": metadata.get("reason_counts", {}),
        "thresholds": metadata.get("thresholds", {}),
    }


def _intraday_cache_readiness(universe: dict[str, Any], cache_rows: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    selected = set(universe["selected_symbols"])
    timeframe_rows = []
    for timeframe in ("5m", "15m", "30m", "1h"):
        rows_by_symbol = cache_rows.get(timeframe, {})
        cached = selected & set(rows_by_symbol)
        row_counts = [rows_by_symbol[symbol]["rows"] for symbol in cached]
        missing = sorted(selected - set(rows_by_symbol))
        timeframe_rows.append(
            {
                "experiment_id": "RC-002-A",
                "timeframe": timeframe,
                "selected_symbols": len(selected),
                "symbols_cached": len(cached),
                "missing_symbols": len(missing),
                "cache_hit_rate": round(len(cached) / len(selected), 6) if selected else 0.0,
                "min_rows": min(row_counts) if row_counts else 0,
                "median_rows": _median(row_counts),
                "max_rows": max(row_counts) if row_counts else 0,
                "first_timestamp_min": min((rows_by_symbol[symbol]["first_timestamp"] for symbol in cached), default=""),
                "last_timestamp_max": max((rows_by_symbol[symbol]["last_timestamp"] for symbol in cached), default=""),
                "decision": _cache_readiness_decision(len(cached), len(selected), min(row_counts) if row_counts else 0),
                "sample_missing_symbols": ",".join(missing[:20]),
            }
        )
    primary_30m = next(row for row in timeframe_rows if row["timeframe"] == "30m")
    decision = (
        "INTRADAY_CACHE_READY_FOR_PLANNED_WAVE"
        if primary_30m["cache_hit_rate"] >= 0.95 and primary_30m["min_rows"] >= 120 and universe["suspicious_selected_count"] == 0
        else "INTRADAY_CACHE_PARTIAL"
        if primary_30m["symbols_cached"] > 0
        else "INTRADAY_CACHE_BLOCKED_MISSING_DATA"
    )
    return {
        "experiment_id": "RC-002-A",
        "decision": decision,
        "universe": universe,
        "timeframe_rows": timeframe_rows,
        "readiness_blockers": _readiness_blockers(universe, timeframe_rows),
        "safety_flags": dict(SAFETY_FLAGS),
    }


def _intraday_matrix_plan(universe: dict[str, Any], cache_rows: dict[str, dict[str, dict[str, Any]]], repo_root: Path) -> dict[str, Any]:
    selected = set(universe["selected_symbols"])
    timeframes = ["15m", "30m", "1h"]
    windows = [20, 50, 100]
    forward_sets = {"fast": [2, 3, 4], "standard": [4, 8, 13], "slow": [8, 13, 21]}
    regimes = ["no_filter", "spy_qqq_positive", "spy_qqq_negative", "gap_day", "high_rvol", "first_hour", "last_hour"]
    microbench_rate = _capacity_001_rows_per_second(repo_root)
    matrix_rows = []
    for timeframe in timeframes:
        rows_by_symbol = cache_rows.get(timeframe, {})
        cached = selected & set(rows_by_symbol)
        symbol_rows = [rows_by_symbol[symbol]["rows"] for symbol in cached]
        min_rows = min(symbol_rows) if symbol_rows else 0
        for window in windows:
            for forward_name, forwards in forward_sets.items():
                required_rows = window + max(forwards) + 20
                available_windows = sum(max(rows_by_symbol[symbol]["rows"] - required_rows, 0) for symbol in cached)
                for regime in regimes:
                    regime_factor = 1.0 if regime == "no_filter" else 0.5
                    estimated_windows = int(available_windows * regime_factor)
                    matrix_rows.append(
                        {
                            "experiment_id": "RC-002-B",
                            "timeframe": timeframe,
                            "window": f"W{window}",
                            "forward_set": forward_name,
                            "regime": regime,
                            "symbols_cached": len(cached),
                            "selected_symbols": len(selected),
                            "cache_hit_rate": round(len(cached) / len(selected), 6) if selected else 0.0,
                            "min_rows": min_rows,
                            "estimated_windows": estimated_windows,
                            "estimated_runtime_seconds": round(estimated_windows / microbench_rate, 6) if microbench_rate else None,
                            "classification": _matrix_classification(len(cached), len(selected), min_rows, estimated_windows, regime),
                            "needs_director_approval": True,
                        }
                    )
    counts = Counter(row["classification"] for row in matrix_rows)
    decision = (
        "MATRIX_PLAN_READY_FOR_SMALL_BATCH"
        if counts.get("READY", 0) >= 9
        else "MATRIX_PLAN_NEEDS_CACHE"
        if counts.get("DATA_MISSING", 0) or counts.get("PARTIAL", 0)
        else "MATRIX_PLAN_INCONCLUSIVE"
    )
    return {
        "experiment_id": "RC-002-B",
        "decision": decision,
        "combination_count": len(matrix_rows),
        "classification_counts": dict(sorted(counts.items())),
        "matrix_rows": matrix_rows,
        "microbench_rows_per_second": round(microbench_rate, 3) if microbench_rate else None,
        "safety_flags": dict(SAFETY_FLAGS),
    }


def _rejected_mining(runtime_root: Path) -> dict[str, Any]:
    evidence_path = runtime_root / "research_evidence" / "_summary.json"
    forensics_path = runtime_root / "research_forensics" / "_forensics.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    forensics = json.loads(forensics_path.read_text(encoding="utf-8")) if forensics_path.exists() else {}
    candidates = list(evidence.get("candidate_manifests", []))
    forensic_rows = list(forensics.get("candidate_forensics", []))
    blocker_counts: Counter[str] = Counter()
    co_occurrence: Counter[str] = Counter()
    family_rows: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in candidates:
        reasons = [_normalize_blocker(reason) for reason in row.get("rejection_reasons", [])]
        reasons = [reason for reason in reasons if reason]
        blocker_counts.update(reasons)
        for left_idx, left in enumerate(sorted(set(reasons))):
            for right in sorted(set(reasons))[left_idx + 1 :]:
                co_occurrence[f"{left}+{right}"] += 1
        key = (row.get("timeframe", "unknown"), f"W{row.get('window_size', 'unknown')}")
        family_rows[key].update(reasons)
    for row in forensic_rows:
        taxonomy = [_normalize_blocker(item) for item in row.get("failure_taxonomy", [])]
        blocker_counts.update(item for item in taxonomy if item)
        for gate in ("cost_x2_result", "fdr_result", "wrc_result", "spa_result", "placebo_adversarial", "market_replay"):
            value = row.get(gate)
            if value == "failed":
                blocker_counts[_normalize_blocker(gate)] += 1
    blocker_rows = [
        {
            "experiment_id": "RC-002-C",
            "blocker": blocker,
            "count": count,
            "blocker_type": _blocker_type(blocker),
        }
        for blocker, count in blocker_counts.most_common()
    ]
    decision = "REJECTED_MINING_READY" if blocker_rows else "REJECTED_MINING_INSUFFICIENT_DATA"
    promising = _promising_search_spaces(family_rows)
    return {
        "experiment_id": "RC-002-C",
        "decision": decision,
        "evidence_path": str(evidence_path) if evidence_path.exists() else None,
        "forensics_path": str(forensics_path) if forensics_path.exists() else None,
        "candidate_count": len(candidates),
        "forensic_count": len(forensic_rows),
        "blocker_rows": blocker_rows,
        "top_co_occurrences": [{"pair": key, "count": value} for key, value in co_occurrence.most_common(12)],
        "promising_search_spaces": promising,
        "safety_flags": dict(SAFETY_FLAGS),
    }


def _capacity_002_throughput(a: dict[str, Any], b: dict[str, Any], c: dict[str, Any], started: str, elapsed: float) -> dict[str, Any]:
    metrics = [
        _metric(
            experiment_id="RC-002-A",
            runner_name="intraday_cache_universe_readiness",
            research_family="intraday",
            universe_policy=a["universe"]["product_policy"],
            symbols_count=a["universe"]["selected_count"],
            timeframe="5m,15m,30m,1h",
            window="cache_coverage_only",
            forward_set="none",
            started_at=started,
            finished_at=_now(),
            elapsed_seconds=round(elapsed, 6),
            windows_processed=sum(row["symbols_cached"] for row in a["timeframe_rows"]),
            clusters_processed=len(a["timeframe_rows"]),
            cache_hit_rate=next(row["cache_hit_rate"] for row in a["timeframe_rows"] if row["timeframe"] == "30m"),
            data_missing_count=sum(row["missing_symbols"] for row in a["timeframe_rows"]),
            blocker_counts={item: 1 for item in a["readiness_blockers"]},
            decision=a["decision"],
        ),
        _metric(
            experiment_id="RC-002-B",
            runner_name="intraday_matrix_dry_run_planner",
            research_family="intraday",
            universe_policy="selected_stock_only_cached",
            symbols_count=a["universe"]["selected_count"],
            timeframe="15m,30m,1h",
            window="W20,W50,W100",
            forward_set="fast,standard,slow",
            started_at=started,
            finished_at=_now(),
            elapsed_seconds=round(elapsed, 6),
            windows_processed=sum(row["estimated_windows"] for row in b["matrix_rows"]),
            clusters_processed=b["combination_count"],
            cache_hit_rate=max(row["cache_hit_rate"] for row in b["matrix_rows"]) if b["matrix_rows"] else 0.0,
            blocker_counts=b["classification_counts"],
            decision=b["decision"],
        ),
        _metric(
            experiment_id="RC-002-C",
            runner_name="rejected_near_miss_mining",
            research_family="intraday",
            universe_policy="existing_rejected_artifacts_only",
            symbols_count=0,
            timeframe="mixed",
            window="existing_reports",
            forward_set="none",
            started_at=started,
            finished_at=_now(),
            elapsed_seconds=round(elapsed, 6),
            windows_processed=c["candidate_count"] + c["forensic_count"],
            clusters_processed=len(c["blocker_rows"]),
            candidates_rejected=c["candidate_count"],
            blocker_counts={row["blocker"]: row["count"] for row in c["blocker_rows"][:20]},
            decision=c["decision"],
        ),
    ]
    return {
        "metrics": metrics,
        "recommended_next_batch": _recommended_next_batch(a, b, c),
        "bottlenecks": _capacity_002_bottlenecks(a, b, c),
        "safety_flags": dict(SAFETY_FLAGS),
    }


def _cache_symbol(path: Path) -> str:
    parts = path.stem.rsplit("_", 2)
    return parts[0] if len(parts) >= 3 else path.name.split("_", 1)[0]


def _cache_timeframe(path: Path) -> str:
    parts = path.stem.split("_")
    return parts[-2] if len(parts) >= 3 else "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _first_existing(root: Path, names: list[str]) -> Path | None:
    for name in names:
        path = root / name
        if path.exists():
            return path
    return None


def _read_csv_rows(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))


def _meaningful_cell(value: str | None, *, allowed: set[str] | None = None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized not in {"", "nan", "none", "null", *(allowed or set())}


def _median(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _cache_readiness_decision(cached: int, selected: int, min_rows: int) -> str:
    if selected == 0 or cached == 0:
        return "DATA_MISSING"
    hit_rate = cached / selected
    if hit_rate >= 0.95 and min_rows >= 120:
        return "READY"
    if hit_rate >= 0.25:
        return "PARTIAL"
    return "DATA_MISSING"


def _readiness_blockers(universe: dict[str, Any], timeframe_rows: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if universe["suspicious_selected_count"]:
        blockers.append("suspicious_selected_product_class")
    for row in timeframe_rows:
        if row["decision"] != "READY":
            blockers.append(f"{row['timeframe']}_{row['decision'].lower()}")
    return blockers


def _capacity_001_rows_per_second(repo_root: Path) -> float:
    summary = repo_root / "research" / "capacity" / "capacity_001_microbench_summary.csv"
    if not summary.exists():
        return 500000.0
    rows = _read_csv_rows(summary)
    for row in rows:
        if row.get("experiment_id") == "CAPACITY-001-INTRADAY-CACHE-PARSE":
            windows = float(row.get("windows_processed") or 0)
            elapsed = float(row.get("elapsed_seconds") or 0)
            if windows > 0 and elapsed > 0:
                return windows / elapsed
    return 500000.0


def _matrix_classification(cached: int, selected: int, min_rows: int, estimated_windows: int, regime: str) -> str:
    if selected == 0 or cached == 0:
        return "DATA_MISSING"
    hit_rate = cached / selected
    if hit_rate < 0.25:
        return "DATA_MISSING"
    if hit_rate < 0.75:
        return "PARTIAL"
    if min_rows < 120 or estimated_windows < 500:
        return "PARTIAL"
    if regime != "no_filter":
        return "NEEDS_DIRECTOR_APPROVAL"
    return "READY"


def _normalize_blocker(reason: str) -> str:
    text = reason.lower()
    mappings = (
        ("drawdown", "drawdown"),
        ("coste x2", "cost_x2"),
        ("cost_x2", "cost_x2"),
        ("oos", "oos"),
        ("walk-forward", "oos"),
        ("fdr", "fdr"),
        ("p_adj", "fdr"),
        ("wrc", "wrc"),
        ("reality", "wrc"),
        ("spa", "spa"),
        ("placebo", "placebo"),
        ("adversarial", "placebo"),
        ("concentracion", "concentration"),
        ("concentración", "concentration"),
        ("diversidad", "concentration"),
        ("simbol", "concentration"),
        ("símbol", "concentration"),
        ("overfit", "overfit"),
        ("bootstrap", "bootstrap"),
        ("edge insuficiente", "edge"),
        ("profit", "edge"),
        ("market replay", "market_replay"),
        ("regime", "regime"),
    )
    for needle, normalized in mappings:
        if needle in text:
            return normalized
    return text.split(":", 1)[0].strip().replace(" ", "_")[:40]


def _blocker_type(blocker: str) -> str:
    if blocker in {"drawdown", "cost_x2", "edge"}:
        return "costs_or_risk"
    if blocker in {"oos", "fdr", "wrc", "spa", "placebo", "bootstrap", "overfit", "market_replay"}:
        return "methodology"
    if blocker in {"concentration", "regime"}:
        return "data_or_regime"
    return "other"


def _promising_search_spaces(family_rows: dict[tuple[str, str], Counter[str]]) -> list[dict[str, Any]]:
    spaces = []
    for (timeframe, window), counts in family_rows.items():
        total = sum(counts.values())
        methodology = sum(counts[key] for key in ("oos", "fdr", "wrc", "spa", "placebo", "bootstrap", "overfit"))
        risk = sum(counts[key] for key in ("drawdown", "cost_x2", "edge"))
        score = max(total - methodology - risk, 0)
        spaces.append(
            {
                "timeframe": timeframe,
                "window": window,
                "blocker_count": total,
                "methodology_blockers": methodology,
                "cost_risk_blockers": risk,
                "priority_score": score,
            }
        )
    return sorted(spaces, key=lambda row: (row["priority_score"], -row["blocker_count"]), reverse=True)[:8]


def _capacity_002_decision(a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> str:
    if c["decision"] == "REJECTED_MINING_INSUFFICIENT_DATA":
        return "RESEARCH_CAPACITY_BLOCKED_BY_DATA"
    if a["decision"] == "INTRADAY_CACHE_READY_FOR_PLANNED_WAVE" and b["decision"] == "MATRIX_PLAN_READY_FOR_SMALL_BATCH":
        return "RESEARCH_CAPACITY_PLAN_EXECUTED_READY_FOR_BATCH"
    if a["decision"] == "INTRADAY_CACHE_PARTIAL" or b["decision"] == "MATRIX_PLAN_NEEDS_CACHE":
        return "RESEARCH_CAPACITY_PLAN_EXECUTED_NEEDS_CACHE"
    return "RESEARCH_CAPACITY_PLAN_EXECUTED_NEEDS_DIRECTOR_DECISION"


def _recommended_next_batch(a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> list[dict[str, Any]]:
    del a, c
    ready = [row for row in b["matrix_rows"] if row["classification"] == "READY"]
    partial_approval = [row for row in b["matrix_rows"] if row["classification"] == "NEEDS_DIRECTOR_APPROVAL"]
    batch = ready[:6] or partial_approval[:6]
    return [
        {
            "timeframe": row["timeframe"],
            "window": row["window"],
            "forward_set": row["forward_set"],
            "regime": row["regime"],
            "classification": row["classification"],
            "estimated_windows": row["estimated_windows"],
            "requires_separate_authorization": True,
        }
        for row in batch
    ]


def _capacity_002_bottlenecks(a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> list[str]:
    bottlenecks = list(a["readiness_blockers"])
    for key, value in b["classification_counts"].items():
        if key != "READY":
            bottlenecks.append(f"matrix_{key.lower()}={value}")
    bottlenecks.extend(row["blocker"] for row in c["blocker_rows"][:5])
    return bottlenecks


def _capacity_002_a_markdown(a: dict[str, Any]) -> str:
    rows = "\n".join(
        f"- {row['timeframe']}: cached={row['symbols_cached']}/{row['selected_symbols']}, hit_rate={row['cache_hit_rate']}, min_rows={row['min_rows']}, decision={row['decision']}"
        for row in a["timeframe_rows"]
    )
    universe = a["universe"]
    return f"""# CAPACITY-002-A Intraday Cache Readiness

Decision: `{a['decision']}`

Universe:
- selected_count: {universe['selected_count']}
- total_candidates: {universe['total_candidates']}
- rejected_count: {universe['rejected_count']}
- product_policy: `{universe['product_policy']}`
- suspicious_selected_count: {universe['suspicious_selected_count']}
- product_class_distribution: `{json.dumps(universe['product_class_distribution'], sort_keys=True)}`

Timeframe coverage:
{rows}

Readiness blockers: `{json.dumps(a['readiness_blockers'], sort_keys=True)}`

Safety: cache-only; no IBKR; no downloads; no signals; no preview; no orders; no candidate approval.
"""


def _capacity_002_b_markdown(b: dict[str, Any]) -> str:
    return f"""# CAPACITY-002-B Intraday Matrix Plan

Decision: `{b['decision']}`

Combination count: {b['combination_count']}
Classification counts: `{json.dumps(b['classification_counts'], sort_keys=True)}`
Microbench rows/sec baseline: `{b['microbench_rows_per_second']}`

The planned matrix covers 15m/30m/1h, W20/W50/W100, fast/standard/slow forward sets, and seven regimes. It was classified from cache coverage and estimated windows only; no wave was executed.

Safety: cache-only; no IBKR; no downloads; no signals; no preview; no orders; no candidate approval.
"""


def _capacity_002_c_markdown(c: dict[str, Any]) -> str:
    blockers = "\n".join(f"- {row['blocker']}: {row['count']} ({row['blocker_type']})" for row in c["blocker_rows"][:15])
    spaces = "\n".join(
        f"- {row['timeframe']} {row['window']}: score={row['priority_score']}, blockers={row['blocker_count']}"
        for row in c["promising_search_spaces"]
    )
    return f"""# CAPACITY-002-C Rejected/Near-Miss Mining

Decision: `{c['decision']}`

Candidates mined: {c['candidate_count']}
Forensic rows mined: {c['forensic_count']}

Top blockers:
{blockers}

Promising search-space hints, for prioritization only:
{spaces}

No rejected candidate was rescued, approved, promoted, signaled, previewed, or submitted.
"""


def _capacity_002_throughput_markdown(throughput: dict[str, Any]) -> str:
    metrics = "\n".join(
        f"- {row['experiment_id']}: decision={row['decision']}, windows={row['windows_processed']}, clusters={row['clusters_processed']}, elapsed={row['elapsed_seconds']}"
        for row in throughput["metrics"]
    )
    batch = "\n".join(
        f"- {row['timeframe']} {row['window']} {row['forward_set']} {row['regime']}: {row['classification']}, estimated_windows={row['estimated_windows']}"
        for row in throughput["recommended_next_batch"]
    )
    return f"""# CAPACITY-002 Throughput Summary

Metrics:
{metrics}

Bottlenecks:
`{json.dumps(throughput['bottlenecks'], sort_keys=True)}`

Recommended next batch, still requiring separate Director authorization:
{batch}

Safety: cache-only plan execution only; no candidates, signals, previews, orders, IBKR, downloads, or gate relaxation.
"""


def _capacity_002_final_report(payload: dict[str, Any], decision: dict[str, Any]) -> str:
    a = payload["rc_002_a"]
    b = payload["rc_002_b"]
    c = payload["rc_002_c"]
    throughput = payload["throughput"]
    return f"""# CAPACITY-002 Final Report

## A. Resumen ejecutivo
CAPACITY-002 ejecutada en modo cache-only/report-only. Decision final: `{payload['decision']}`. Se completaron RC-002-A, RC-002-B y RC-002-C; no se ejecuto wave pesada ni se aprobo candidato alguno.

## B. Path real usado
`{Path.cwd()}`

## C. Rama/commit/push
Rama `feature/research-capacity-001`; commit/push se registran al cierre operativo.

## D. RC-002-A intraday cache/universe readiness
Decision `{a['decision']}`. Universo selected_count={a['universe']['selected_count']}, suspicious_selected_count={a['universe']['suspicious_selected_count']}. 30m coverage={next(row['cache_hit_rate'] for row in a['timeframe_rows'] if row['timeframe'] == '30m')}.

## E. RC-002-B matrix dry-run plan
Decision `{b['decision']}`. Combinaciones={b['combination_count']}; classification_counts=`{json.dumps(b['classification_counts'], sort_keys=True)}`.

## F. RC-002-C rejected/near-miss mining
Decision `{c['decision']}`. Candidates={c['candidate_count']}; forensics={c['forensic_count']}; top_blockers=`{json.dumps(c['blocker_rows'][:8], sort_keys=True)}`.

## G. Throughput summary
Ver `CAPACITY_002_THROUGHPUT_SUMMARY.md` y `capacity_002_throughput_summary.csv/json`.

## H. Bottlenecks found
`{json.dumps(throughput['bottlenecks'], sort_keys=True)}`

## I. Recommended next batch
`{json.dumps(throughput['recommended_next_batch'], sort_keys=True)}`

## J. Tests/validaciones
Validaciones de cierre esperadas: py_compile, pytest focal research_capacity, ruff, git diff --check, JSON validation, security scan y docker build backend si viable.

## K. Decisión CAPACITY-002
`{decision['decision']}`

## L. Confirmación seguridad
No live, no paper, no ordenes, no senales, no preview, no IBKR, no descargas, no gh, no main push, no candidate approval, no promotion, no gate relaxation.

## M. Siguiente decisión esperada
Si Direccion acepta el estado, elegir una micro-wave o batch cache-only pequeno con autorizacion separada, todavia sin candidate approval ni senales.
"""


def _schema_markdown(schema: dict[str, Any]) -> str:
    fields = "\n".join(f"- `{field}`" for field in schema["required_fields"])
    return f"# CAPACITY-001 Metrics Schema\n\nSchema version: `{schema['schema_version']}`\n\nRequired fields:\n{fields}\n\nSafety invariants: cache-only, no IBKR, no orders, no signals, no preview, no candidate approval, no downloads.\n"


def _microbench_markdown(payload: dict[str, Any]) -> str:
    metrics = "\n".join(
        f"- {row['experiment_id']}: decision={row['decision']}, elapsed={row['elapsed_seconds']:.6f}s, windows={row['windows_processed']}, clusters={row['clusters_processed']}"
        for row in payload["metrics"]
    )
    return f"# CAPACITY-001 Microbench Summary\n\nDecision: `{payload['decision']}`\n\nRuntime root: `{payload['runtime_root']}`\n\nCache files sampled: {payload['cache_files_sampled']} / {payload['cache_files_available']}\nRows seen: {payload['rows_seen']}\n\n{metrics}\n\nNo IBKR, orders, signals, preview, downloads, or candidate approval were used.\n"


def _inventory_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# CAPACITY-001 Research Surface Inventory",
        "",
        "## Summary",
        f"- Daily modules: {len(inventory['daily_swing_modules'])}",
        f"- Intraday modules: {len(inventory['intraday_modules'])}",
        f"- Research docs: {inventory['research_docs']}",
        f"- GAP reports: {inventory['gap_reports']}",
        f"- Cache files: {inventory['cache_files']}",
        f"- Classified surfaces: {inventory['surface_row_count']}",
        "",
        "## Classified Surfaces",
    ]
    for row in inventory["surface_rows"]:
        safety = []
        if row["research_only"]:
            safety.append("research-only")
        if row["dry_run_capable"]:
            safety.append("dry-run")
        if row["cache_only_capable"]:
            safety.append("cache-only")
        if row["ibkr_required"]:
            safety.append("IBKR-required")
        if row["can_generate_signals"]:
            safety.append("can-generate-signals")
        if row["can_generate_preview_or_orders"]:
            safety.append("can-generate-preview-or-orders")
        lines.extend(
            [
                f"### {row['surface']}",
                f"- Path: `{row['path']}`",
                f"- Family: `{row['family']}`",
                f"- Flags: {', '.join(safety) if safety else 'none'}",
                f"- Candidate-producing: {row['can_generate_candidates']}",
                f"- Notes: {row['notes']}",
                "",
            ]
        )
    return "\n".join(lines)


def _queue_markdown(queue: list[dict[str, Any]]) -> str:
    lines = ["# CAPACITY-001 Experiment Queue", ""]
    for row in queue:
        lines.append(f"## {row['priority']}. {row['experiment_id']} - {row['name']}")
        lines.append(f"- Priority score: {row['priority_score']}")
        lines.append(f"- Priority rationale: {row['priority_rationale']}")
        lines.append(f"- EVI: {row['expected_value_of_information']}")
        lines.append(f"- Data required: {row['data_required']}")
        lines.append(f"- Cache required: {row['cache_required']}")
        lines.append(f"- Estimated runtime: {row['estimated_runtime']}")
        lines.append(f"- Safety requirements: {row['safety_requirements']}")
        lines.append(f"- Gates required: {row['gates_required']}")
        lines.append(f"- Success metrics: {row['success_metrics']}")
        lines.append(f"- Blocker conditions: {row['blocker_conditions']}")
        lines.append(f"- Needs Director approval: {row['needs_director_approval']}")
        lines.append("")
    return "\n".join(lines)


def _final_report(decision: dict[str, Any], inventory: dict[str, Any], microbench: dict[str, Any], queue: list[dict[str, Any]]) -> str:
    blocked = ", ".join(decision["requires_director_approval"]) or "none"
    allowed = ", ".join(decision["allowed_experiments_after_director_authorizes_capacity_002"]) or "none"
    return f"""AQUI CLAW - Tarea T-RESEARCH-CAPACITY-001 - Fase final - Estado OK

# CAPACITY-001 Final Report

## A. Resumen ejecutivo
Decision solicitada: Direccion puede evaluar si autoriza `T-RESEARCH-CAPACITY-002`.

Resultado: CAPACITY-001 queda en `{decision['decision']}`. Se definio el esquema de metricas, se inventario la superficie research, se ejecuto microbench seguro cache-only y se creo cola priorizada. No se aprobaron candidatos.

Riesgo principal: cache/search-space sigue siendo el cuello de botella; no hay paper_candidate ni shadow_candidate.

## B. Path real usado
`{Path.cwd()}`

## C. Rama/commit/push
Rama `feature/research-capacity-001`; commit/push se registran fuera de este documento al cerrar la tarea.

## D. Research surface inventory
- Daily modules: {len(inventory['daily_swing_modules'])}
- Intraday modules: {len(inventory['intraday_modules'])}
- Research docs: {inventory['research_docs']}
- GAP reports: {inventory['gap_reports']}
- Cache files: {inventory['cache_files']}
- Cache timeframes: `{json.dumps(inventory['cache_timeframes'], sort_keys=True)}`
- Classified surfaces: {inventory['surface_row_count']}
- Inventory artifacts: `CAPACITY_001_RESEARCH_SURFACE_INVENTORY.md`, `capacity_001_research_surface_inventory.csv`, `capacity_001_research_surface_inventory.json`

## E. Capacity metrics schema
`CAPACITY_001_METRICS_SCHEMA.md` define {len(REQUIRED_METRIC_FIELDS)} campos obligatorios.

## F. Microbench results or blocker
Decision microbench: `{microbench['decision']}`. Cache sampled {microbench['cache_files_sampled']} de {microbench['cache_files_available']}; rows_seen={microbench['rows_seen']}; elapsed_seconds={microbench['elapsed_seconds']}.

## G. Experiment queue prioritized
{len(queue)} experimentos priorizados; el primero es `{queue[0]['experiment_id']}`.

Allowed only after Director authorizes CAPACITY-002: `{allowed}`.

Require separate Director approval: `{blocked}`.

## H. Lab bottlenecks identified
Blockers principales: cache coverage, leakage controls, sample size/effective sample, FDR/WRC/SPA-light, cost_x2, OOS, drawdown y placebo gates.

## I. Throughput metrics baseline
Ver `capacity_001_microbench_summary.csv` y runtime JSON/CSV no versionados.

## J. Safety confirmation
live_allowed=false; paper_allowed=false; orders_allowed=false; order_code_changed=false; gates_relaxed=false; no signals; no preview; no IBKR; no downloads; no gh; no main push.

## K. Tests/validaciones
Validaciones de cierre esperadas: py_compile, pytest focal, ruff, git diff --check, JSON validation, security scan y docker build backend.

## L. Decision CAPACITY-001
`{decision['decision']}`

## M. Siguiente decision esperada
Si Direccion acepta, ejecutar `T-RESEARCH-CAPACITY-002` con primeros experimentos cache-only priorizados. Ningun experimento podra aprobar candidatos ni producir senales/paper sin tarea separada.
"""
