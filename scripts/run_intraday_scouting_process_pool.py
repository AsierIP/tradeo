#!/usr/bin/env python3
"""Run intraday Research process-pool scouting with near-miss persistence.

The normal optimized process-pool path stores only validation-passed candidates in
workers to keep benchmark/runtime overhead low. When the system has produced no
usable patterns for days, run this script once or on demand with
`--store-rejected` so the DB contains the near-misses and exact rejection
reasons needed by `diagnose_intraday_pattern_funnel.py`.

This script does not relax quality gates and does not promote anything beyond
what `ValidationGate` already permits.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
import json
import multiprocessing
import os
import sys
import time
from typing import Any

from tradeo.core.config import get_settings
from tradeo.modules.resource_policy.enforcement import blocked_job_status, decide_with_market_session_policy
from tradeo.modules.resource_policy.market_session_resource_policy import JobType
from tradeo.tasks import worker

_BENCHMARK_REPORT_MODE_ENV = "TRADEO_DISCOVERY_BENCHMARK_REPORT_MODE"
_NATIVE_THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-recent-duplicates", action="store_true")
    parser.add_argument(
        "--store-rejected",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Persist rejected/near-miss candidates for diagnosis. Default: true.",
    )
    parser.add_argument(
        "--start-method",
        choices=("auto", "default", "fork", "forkserver", "spawn"),
        default="auto",
    )
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    os.environ[_BENCHMARK_REPORT_MODE_ENV] = "json_only"
    if args.start_method:
        os.environ[worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV] = args.start_method

    settings = get_settings()
    policy_decision = decide_with_market_session_policy(
        JobType.RESEARCH_HEAVY,
        "intraday_research",
        settings=settings,
    )
    if not policy_decision.allowed:
        payload = {
            "decision": "blocked_resource_policy",
            "resource_policy": policy_decision.to_dict(),
            "research_result": blocked_job_status(policy_decision),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 5

    jobs = worker._intraday_research_process_jobs(
        settings,
        allow_recent_duplicates=bool(args.allow_recent_duplicates),
    )
    if not jobs:
        payload = {"status": "noop", "reason": "intraday_research_process_pool_empty"}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1

    max_workers = min(max(1, int(settings.intraday_research_process_workers or 1)), len(jobs))
    native_threads = max(1, int(settings.intraday_research_native_threads_per_process or 1))
    started = time.monotonic()
    runs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    worker_results: list[dict[str, Any]] = []

    executor_kwargs: dict[str, Any] = {
        "max_workers": max_workers,
        "initializer": _process_initializer,
        "initargs": (native_threads,),
    }
    start_method = _selected_start_method()
    if start_method is not None:
        executor_kwargs["mp_context"] = multiprocessing.get_context(start_method)

    with ProcessPoolExecutor(**executor_kwargs) as executor:
        futures = {
            executor.submit(_run_scouting_job, job, bool(args.store_rejected)): (submit_order, job)
            for submit_order, job in enumerate(jobs)
        }
        for future in as_completed(futures):
            submit_order, job = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - report all failed chunks.
                if isinstance(exc, BrokenProcessPool):
                    errors.append(
                        {
                            "timeframe": job.timeframe,
                            "chunk": f"{job.chunk_index + 1}_of_{job.chunk_count}",
                            "error": f"BrokenProcessPool: {exc}",
                        }
                    )
                else:
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

    elapsed = round(time.monotonic() - started, 3)
    status = "ok" if not errors else ("degraded" if runs or skipped else "error")
    payload = {
        "status": status,
        "reason": "intraday_scouting_process_pool_completed",
        "store_rejected": bool(args.store_rejected),
        "elapsed_wall_s": elapsed,
        "summary": {
            "runs": len(runs),
            "windows": sum(int(run.get("windows_sampled") or 0) for run in runs),
            "clusters": sum(int(run.get("clusters_evaluated") or 0) for run in runs),
            "accepted": sum(int(run.get("accepted_patterns") or 0) for run in runs),
            "rejected": sum(int(run.get("rejected_patterns") or 0) for run in runs),
            "skipped": len(skipped),
            "errors": len(errors),
        },
        "details": {
            "process_workers": max_workers,
            "jobs": len(jobs),
            "chunks": jobs[0].chunk_count,
            "native_threads_per_process": native_threads,
            "process_start_method": start_method or "default",
            "allow_recent_duplicates": bool(args.allow_recent_duplicates),
            "runs": runs,
            "skipped": skipped,
            "errors": errors,
            "worker_results": sorted(
                worker_results,
                key=lambda item: (str(item.get("timeframe") or ""), int(item.get("chunk_index") or 0)),
            ),
        },
    }
    if not args.json_only:
        _print_human(payload)
        print("\nJSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status in {"ok", "degraded"} and runs else 1


def _process_initializer(native_threads: int) -> None:
    _set_native_threads(native_threads)
    worker._reset_intraday_research_process_db_state()
    cache_clear = getattr(get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def _run_scouting_job(job: worker.IntradayResearchProcessJob, store_rejected: bool) -> dict[str, Any]:
    started = time.monotonic()
    cache_clear = getattr(worker.get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    settings = worker.get_settings()
    native_threads = max(1, int(settings.intraday_research_native_threads_per_process or 1))
    _set_native_threads(native_threads)
    worker._reset_intraday_research_process_worker_state(job.pool_run_id)

    def run_once() -> dict[str, Any]:
        return worker._run_intraday_research(
            settings,
            timeframes=[job.timeframe],
            symbol_chunk=(job.chunk_index, job.chunk_count),
            chunk_symbols=job.symbols,
            store_rejected=store_rejected,
            allow_recent_duplicates=job.allow_recent_duplicates,
        )

    try:
        from threadpoolctl import threadpool_limits
    except ImportError:
        result = run_once()
    else:
        with threadpool_limits(limits=native_threads):
            result = run_once()
    return worker._intraday_research_process_worker_result(result, job, started)


def _selected_start_method() -> str | None:
    requested = os.getenv(worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV, "auto").strip().lower()
    available = multiprocessing.get_all_start_methods()
    if requested in {"", "auto"}:
        if sys.platform.startswith("linux") and "fork" in available:
            return "fork"
        return None
    if requested in {"default", "none"}:
        return None
    if requested in available:
        return requested
    return None


def _set_native_threads(native_threads: int) -> None:
    thread_count = str(max(1, int(native_threads)))
    for env_var in _NATIVE_THREAD_ENV_VARS:
        os.environ[env_var] = thread_count


def _print_human(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    print("Intraday scouting process-pool")
    print("==============================")
    print(
        f"status={payload['status']} wall={payload['elapsed_wall_s']}s "
        f"runs={summary['runs']} windows={summary['windows']} clusters={summary['clusters']} "
        f"accepted={summary['accepted']} rejected={summary['rejected']} "
        f"errors={summary['errors']} skipped={summary['skipped']}"
    )
    print(f"store_rejected={payload['store_rejected']}")


if __name__ == "__main__":
    raise SystemExit(main())
