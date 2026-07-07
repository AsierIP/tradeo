#!/usr/bin/env python3
"""Plan and score Tradeo intraday Research historical-capacity loops.

Standalone helper: it prints candidate benchmark commands that expand history and
window budgets, and scores JSON emitted by run_intraday_process_pool_benchmark.py.
Quality is the gate: speed only counts if windows/clusters/errors/skips do not
regress; deeper history can win if windows per second remains efficient.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.core.config import get_settings  # noqa: E402
from tradeo.modules.resource_policy.enforcement import decide_with_market_session_policy  # noqa: E402
from tradeo.modules.resource_policy.market_session_resource_policy import JobType  # noqa: E402

BASELINE = {
    "db_group": "2968-2979",
    "wall_s": 10.235,
    "speed_accept_s": 9.928,
    "windows": 9_300,
    "clusters": 118,
    "errors": 0,
    "skips": 0,
}
DEFAULT_PERIODS = "30d,45d,60d,90d,120d,180d"
DEFAULT_CHUNKS = "6,7"


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    period: str
    period_days: int
    chunks: int
    workers: int
    native_threads: int
    history_multiplier: float
    max_windows_per_symbol: int
    max_total_windows: int
    command: str


@dataclass(frozen=True, slots=True)
class Score:
    candidate: str
    runs: int
    valid_runs: int
    median_wall_s: float | None
    windows: int
    clusters: int
    errors: int
    skipped: int
    windows_per_second: float | None
    accepted_for_speed: bool
    accepted_for_capacity: bool
    decision: str
    reasons: list[str]


def period_days(period: str) -> int:
    raw = str(period).strip().lower().replace(" ", "")
    units = (
        ("months", 30), ("month", 30), ("mon", 30), ("mo", 30),
        ("weeks", 7), ("week", 7), ("w", 7),
        ("years", 365), ("year", 365), ("yr", 365), ("y", 365),
        ("days", 1), ("day", 1), ("d", 1),
    )
    for unit, multiplier in units:
        if raw.endswith(unit):
            value = raw[: -len(unit)]
            if not value:
                raise ValueError(f"period has no numeric value: {period!r}")
            return max(1, int(math.ceil(float(value) * multiplier)))
    if raw.isdigit():
        return max(1, int(raw))
    raise ValueError(f"unsupported period format: {period!r}")


def env_command(*, period: str, chunks: int, workers: int, native_threads: int,
                max_windows_per_symbol: int, max_total_windows: int) -> str:
    env = {
        "TRADEO_DISCOVERY_BENCHMARK_REPORT_MODE": "json_only",
        "TRADEO_INTRADAY_RESEARCH_ADAPTIVE_CHUNKS": "false",
        "TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS": str(max_total_windows),
        "TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL": str(max_windows_per_symbol),
        "TRADEO_INTRADAY_RESEARCH_NATIVE_THREADS_PER_PROCESS": str(native_threads),
        "TRADEO_INTRADAY_RESEARCH_PARALLEL_SYMBOL_CHUNKS": str(chunks),
        "TRADEO_INTRADAY_RESEARCH_PERIOD": period,
        "TRADEO_INTRADAY_RESEARCH_PROCESS_WORKERS": str(workers),
        "TRADEO_INTRADAY_RESEARCH_REFRESH_MARKET_DATA_ENABLED": "false",
        "TRADEO_MARKET_DATA_CACHE_DIR": "/app/artifacts/runtime/ohlcv_cache",
        "TRADEO_UNIVERSE_SNAPSHOT_DIR": "/app/artifacts/runtime/universe_snapshots",
    }
    prefix = " ".join(f"{key}={value}" for key, value in sorted(env.items()))
    return (
        f"{prefix} docker compose run --rm -T backend "
        "python /app/scripts/run_intraday_process_pool_benchmark.py "
        "--allow-recent-duplicates"
    )


def plan(args: argparse.Namespace) -> dict[str, Any]:
    periods = [item.strip() for item in args.periods.split(",") if item.strip()]
    chunks = [int(item.strip()) for item in args.chunks.split(",") if item.strip()]
    candidates: list[Candidate] = []
    for period in periods:
        days = period_days(period)
        raw_multiplier = max(1.0, days / max(1, args.base_period_days))
        multiplier = raw_multiplier ** max(0.0, args.growth_power)
        windows_per_symbol = min(
            args.max_windows_per_symbol_cap,
            max(args.base_windows_per_symbol, math.ceil(args.base_windows_per_symbol * multiplier)),
        )
        total_windows = min(
            args.max_total_windows_cap,
            max(args.base_total_windows, math.ceil(args.base_total_windows * multiplier)),
        )
        for chunk_count in chunks:
            candidates.append(
                Candidate(
                    name=f"period_{period}_chunks_{chunk_count}",
                    period=period,
                    period_days=days,
                    chunks=chunk_count,
                    workers=args.workers,
                    native_threads=args.native_threads,
                    history_multiplier=round(raw_multiplier, 3),
                    max_windows_per_symbol=int(windows_per_symbol),
                    max_total_windows=int(total_windows),
                    command=env_command(
                        period=period,
                        chunks=chunk_count,
                        workers=args.workers,
                        native_threads=args.native_threads,
                        max_windows_per_symbol=int(windows_per_symbol),
                        max_total_windows=int(total_windows),
                    ),
                )
            )
    return {
        "baseline": BASELINE,
        "policy": {
            "quality_first": True,
            "require_two_clean_runs": True,
            "reject_on_errors_or_skips": True,
            "speed_winner": "median wall <= 9.928s with equal or better quality",
            "capacity_winner": "more windows/history if windows/sec remains efficient",
        },
        "candidates": [asdict(candidate) for candidate in candidates],
        "agent_tasks": agent_tasks(),
    }


def load_runs(paths: list[Path]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("runs"), list):
            runs.extend(item for item in payload["runs"] if isinstance(item, dict))
        elif isinstance(payload, list):
            runs.extend(item for item in payload if isinstance(item, dict))
        else:
            raise ValueError(f"unsupported benchmark JSON shape: {path}")
    return runs


def score(runs: list[dict[str, Any]], args: argparse.Namespace) -> Score:
    reasons: list[str] = []
    valid = [run for run in runs if bool(run.get("valid"))]
    walls = [as_float(run.get("elapsed_wall_s")) for run in valid]
    clean_walls = [wall for wall in walls if wall is not None]
    windows = sum(as_int(run.get("windows")) or 0 for run in valid)
    clusters = sum(as_int(run.get("clusters")) or 0 for run in valid)
    errors = sum(len(run.get("errors") or []) for run in runs)
    skipped = sum(as_int(run.get("skipped")) or 0 for run in runs)
    median_wall = round(float(median(clean_walls)), 3) if clean_walls else None
    total_wall = max(sum(clean_walls), 0.001)
    wps = round(windows / total_wall, 3) if clean_walls and windows else None

    if len(valid) < 2:
        reasons.append("needs_two_clean_runs")
    if errors:
        reasons.append("errors_present")
    if skipped:
        reasons.append("skipped_runs_present")
    if windows <= 0:
        reasons.append("zero_windows")
    if clusters <= 0:
        reasons.append("zero_clusters")
    if valid and clusters / len(valid) < BASELINE["clusters"] * 0.85:
        reasons.append("cluster_count_regression")

    speed_ok = not reasons and median_wall is not None
    speed_ok = speed_ok and median_wall <= BASELINE["speed_accept_s"]
    capacity_target = math.ceil(BASELINE["windows"] * args.min_capacity_multiplier)
    baseline_wps = BASELINE["windows"] / BASELINE["wall_s"]
    capacity_ok = not reasons and windows >= capacity_target * max(1, len(valid))
    capacity_ok = capacity_ok and wps is not None
    capacity_ok = capacity_ok and wps >= baseline_wps * args.min_efficiency_ratio
    if not speed_ok and median_wall is not None and median_wall > BASELINE["speed_accept_s"]:
        reasons.append("speed_threshold_not_met")
    if not capacity_ok and windows > 0:
        reasons.append("capacity_or_efficiency_threshold_not_met")

    if speed_ok:
        decision = "keep_speed_winner"
    elif capacity_ok:
        decision = "keep_capacity_winner"
    else:
        decision = "reject_or_continue_loop"
    return Score(
        candidate=args.candidate,
        runs=len(runs),
        valid_runs=len(valid),
        median_wall_s=median_wall,
        windows=windows,
        clusters=clusters,
        errors=errors,
        skipped=skipped,
        windows_per_second=wps,
        accepted_for_speed=speed_ok,
        accepted_for_capacity=capacity_ok,
        decision=decision,
        reasons=dedupe(reasons),
    )


def agent_tasks() -> list[dict[str, str]]:
    return [
        {
            "agent": "Auditor calidad",
            "task": "bloquear si bajan ventanas, clusters, muestras o trazabilidad",
        },
        {
            "agent": "Optimizador rendimiento",
            "task": "perfilar phase_timings y worker_tail; proponer parches reversibles",
        },
        {
            "agent": "Explorador historico",
            "task": "probar mas periodos con presupuestos de ventanas escalados",
        },
        {
            "agent": "Red team metodologico",
            "task": "buscar cache bias, survivorship, leakage, duplicados y overfitting",
        },
    ]


def as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", default=DEFAULT_PERIODS)
    parser.add_argument("--chunks", default=DEFAULT_CHUNKS)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--native-threads", type=int, default=1)
    parser.add_argument("--base-period-days", type=int, default=30)
    parser.add_argument("--base-windows-per-symbol", type=int, default=300)
    parser.add_argument("--base-total-windows", type=int, default=8_000)
    parser.add_argument("--max-windows-per-symbol-cap", type=int, default=2_400)
    parser.add_argument("--max-total-windows-cap", type=int, default=80_000)
    parser.add_argument("--growth-power", type=float, default=1.0)
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--candidate", default="manual_candidate")
    parser.add_argument("--benchmark-json", action="append", type=Path, default=[])
    parser.add_argument("--min-capacity-multiplier", type=float, default=1.25)
    parser.add_argument("--min-efficiency-ratio", type=float, default=0.65)
    args = parser.parse_args()

    policy_decision = decide_with_market_session_policy(
        JobType.RESEARCH_HEAVY,
        "research",
        settings=get_settings(),
    )
    if not policy_decision.allowed:
        print(
            json.dumps(
                {
                    "decision": "blocked_resource_policy",
                    "resource_policy": policy_decision.to_dict(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 5

    if args.score:
        if not args.benchmark_json:
            parser.error("--score requires --benchmark-json")
        result = score(load_runs(args.benchmark_json), args)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.accepted_for_speed or result.accepted_for_capacity else 2

    print(json.dumps(plan(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
