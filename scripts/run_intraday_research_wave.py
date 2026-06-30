#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
import json
import multiprocessing
from pathlib import Path
import time
from typing import Any

from tradeo.core.config import Settings, get_settings
from tradeo.services.intraday_research_readiness import (
    IntradayResearchReadinessGate,
    IntradayResearchWaveSpec,
)
from tradeo.tasks import worker


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an intraday research wave only if cache/data readiness passes."
    )
    parser.add_argument("--execute", action="store_true", help="Actually run scouting after readiness passes.")
    parser.add_argument("--allow-recent-duplicates", action="store_true")
    parser.add_argument(
        "--store-rejected",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Persist rejected near-miss candidates during diagnostic waves. Default: true.",
    )
    parser.add_argument("--universe-file", default=None)
    parser.add_argument("--period", default=None)
    parser.add_argument("--timeframes", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--window-sizes", default=None)
    parser.add_argument("--forward-bars", default=None)
    parser.add_argument("--max-total-windows", type=int, default=None)
    parser.add_argument("--max-windows-per-symbol", type=int, default=None)
    parser.add_argument("--min-cache-coverage", type=float, default=0.90)
    parser.add_argument("--min-rows-per-symbol", type=int, default=1)
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    spec = IntradayResearchWaveSpec.from_settings(
        settings,
        universe_file=args.universe_file,
        period=args.period,
        timeframes=tuple(_csv_str(args.timeframes)) if args.timeframes else None,
        limit=args.limit,
        window_sizes=tuple(_csv_int(args.window_sizes)) if args.window_sizes else None,
        forward_bars=tuple(_csv_int(args.forward_bars)) if args.forward_bars else None,
        max_total_windows=args.max_total_windows,
        max_windows_per_symbol=args.max_windows_per_symbol,
        min_cache_coverage=args.min_cache_coverage,
        min_rows_per_symbol=args.min_rows_per_symbol,
    )
    gate = IntradayResearchReadinessGate(settings=settings)
    readiness = gate.evaluate(spec)
    wave_result: dict[str, Any] = {
        "schema_version": 1,
        "mode": "execute" if args.execute else "dry_run",
        "store_rejected": bool(args.store_rejected),
        "readiness": readiness.manifest,
        "research_result": None,
    }
    status_code = 0
    if not readiness.ready:
        wave_result["decision"] = "blocked_data_missing"
        status_code = 2
    elif not args.execute:
        wave_result["decision"] = "ready_dry_run"
    else:
        started = time.monotonic()
        result = _run_wave_process_pool(
            settings,
            allow_recent_duplicates=bool(args.allow_recent_duplicates),
            store_rejected=bool(args.store_rejected),
        )
        wave_result["research_result"] = result
        wave_result["elapsed_wall_s"] = round(time.monotonic() - started, 3)
        wave_result["decision"] = "executed"
        status_code = 0 if result.get("status") in {"ok", "degraded"} else 1

    manifest_hash = readiness.manifest_hash
    manifest_path = Path(
        args.manifest_path
        or settings.artifacts_path
        / "runtime"
        / f"intraday_research_wave_{manifest_hash[:12]}.json"
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(wave_result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    summary = {
        "decision": wave_result["decision"],
        "manifest_path": str(manifest_path),
        "ready": readiness.ready,
        "coverage": readiness.coverage,
        "ok": readiness.ok,
        "total": readiness.total,
        "execute": bool(args.execute),
        "store_rejected": bool(args.store_rejected),
        "research_status": (wave_result.get("research_result") or {}).get("status"),
    }
    if not args.json_only:
        print(
            f"decision={summary['decision']} ready={summary['ready']} "
            f"coverage={summary['coverage']:.2%} ok={summary['ok']}/{summary['total']} "
            f"store_rejected={summary['store_rejected']} manifest={manifest_path}"
        )
        print("JSON:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return status_code


def _run_wave_process_pool(
    settings: Settings,
    *,
    allow_recent_duplicates: bool,
    store_rejected: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    jobs = worker._intraday_research_process_jobs(  # noqa: SLF001
        settings,
        allow_recent_duplicates=allow_recent_duplicates,
    )
    if not jobs:
        return {
            "status": "noop",
            "reason": "intraday_research_process_pool_empty",
            "details": {
                "component": "research",
                "process_pool": True,
                "store_rejected": store_rejected,
            },
        }

    max_workers = min(max(1, int(settings.intraday_research_process_workers or 1)), len(jobs))
    native_threads = max(1, int(settings.intraday_research_native_threads_per_process or 1))
    start_method = worker._intraday_research_process_start_method()  # noqa: SLF001
    executor_kwargs: dict[str, Any] = {
        "max_workers": max_workers,
        "initializer": _process_initializer,
        "initargs": (native_threads,),
    }
    if start_method is not None:
        executor_kwargs["mp_context"] = multiprocessing.get_context(start_method)

    runs: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    worker_results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(**executor_kwargs) as executor:
        futures = {
            executor.submit(_run_wave_process_worker, job, store_rejected): (submit_order, job)
            for submit_order, job in enumerate(jobs)
        }
        for future in as_completed(futures):
            submit_order, job = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - report failed chunks and continue.
                errors.append(
                    {
                        "timeframe": job.timeframe,
                        "chunk": f"{job.chunk_index + 1}_of_{job.chunk_count}",
                        "error": f"{type(exc).__name__}: {exc}",
                        "pool_broken": isinstance(exc, BrokenProcessPool),
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

    status = "ok" if not errors else ("degraded" if runs or skipped else "error")
    return {
        "status": status,
        "reason": "intraday_research_wave_process_pool_completed",
        "details": {
            "component": "research",
            "process_pool": True,
            "process_workers": max_workers,
            "jobs": len(jobs),
            "chunks": jobs[0].chunk_count,
            "configured_chunks": worker._intraday_research_parallel_symbol_chunks(settings),  # noqa: SLF001
            "adaptive_chunks": worker._intraday_research_adaptive_chunks_enabled(),  # noqa: SLF001
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


def _process_initializer(native_threads: int) -> None:
    worker._set_intraday_research_native_threads(native_threads)  # noqa: SLF001
    worker._reset_intraday_research_process_db_state()  # noqa: SLF001
    cache_clear = getattr(get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def _run_wave_process_worker(
    job: worker.IntradayResearchProcessJob,
    store_rejected: bool,
) -> dict[str, Any]:
    started = time.monotonic()
    cache_clear = getattr(worker.get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()
    settings = worker.get_settings()
    native_threads = max(1, int(settings.intraday_research_native_threads_per_process or 1))
    worker._set_intraday_research_native_threads(native_threads)  # noqa: SLF001
    worker._reset_intraday_research_process_worker_state(job.pool_run_id)  # noqa: SLF001

    def run_once() -> dict[str, Any]:
        return worker._run_intraday_research(  # noqa: SLF001
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
    return worker._intraday_research_process_worker_result(result, job, started)  # noqa: SLF001


def _csv_str(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _csv_int(raw: str) -> list[int]:
    return [int(item.strip()) for item in str(raw).split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
