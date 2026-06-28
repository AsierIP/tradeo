#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from statistics import mean
import time
from typing import Any

from tradeo.core.config import get_settings
from tradeo.tasks import worker

_BENCHMARK_REPORT_MODE_ENV = "TRADEO_DISCOVERY_BENCHMARK_REPORT_MODE"
_CLUSTER_PROFILE_ENV = "TRADEO_DISCOVERY_CLUSTER_PROFILE"
_CLUSTER_PROFILE_INTERVAL_MS_ENV = "TRADEO_DISCOVERY_CLUSTER_PROFILE_INTERVAL_MS"
_CLUSTER_PROFILE_TOP_N_ENV = "TRADEO_DISCOVERY_CLUSTER_PROFILE_TOP_N"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the intraday research process-pool benchmark.")
    parser.add_argument(
        "--allow-recent-duplicates",
        action="store_true",
        help="Bypass the recent equivalent-run guard inside process-pool workers.",
    )
    parser.add_argument(
        "--start-method",
        choices=("auto", "default", "fork", "forkserver", "spawn"),
        help=(
            "Multiprocessing start method for this benchmark. "
            "Defaults to the worker's TRADEO_INTRADAY_RESEARCH_PROCESS_START_METHOD behavior."
        ),
    )
    parser.add_argument(
        "--keep-pool",
        action="store_true",
        help="Do not shut down the module process pool before running.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of sequential benchmark runs to execute in the same parent process.",
    )
    parser.add_argument(
        "--sleep-between",
        type=float,
        default=0.0,
        help="Seconds to sleep between repeated runs while keeping the process pool alive.",
    )
    parser.add_argument(
        "--write-markdown-reports",
        action="store_true",
        help=(
            "Also write human Markdown discovery reports. "
            "By default this benchmark writes JSON reports only."
        ),
    )
    parser.add_argument(
        "--profile-clustering",
        action="store_true",
        help="Enable low-overhead stack sampling inside ClusterResearchEngine.discover.",
    )
    parser.add_argument(
        "--cluster-profile-interval-ms",
        type=float,
        default=None,
        help="Sampling interval for --profile-clustering. Defaults to 25 ms.",
    )
    parser.add_argument(
        "--cluster-profile-top-n",
        type=int,
        default=None,
        help="Number of sampled clustering frames to keep per run. Defaults to 12.",
    )
    args = parser.parse_args()

    if args.start_method:
        os.environ[worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV] = args.start_method
    if args.write_markdown_reports:
        os.environ.pop(_BENCHMARK_REPORT_MODE_ENV, None)
    else:
        os.environ[_BENCHMARK_REPORT_MODE_ENV] = "json_only"
    if args.profile_clustering:
        os.environ[_CLUSTER_PROFILE_ENV] = "1"
    if args.cluster_profile_interval_ms is not None:
        os.environ[_CLUSTER_PROFILE_INTERVAL_MS_ENV] = str(float(args.cluster_profile_interval_ms))
    if args.cluster_profile_top_n is not None:
        os.environ[_CLUSTER_PROFILE_TOP_N_ENV] = str(int(args.cluster_profile_top_n))
    if not args.keep_pool:
        worker._shutdown_intraday_research_process_pool()

    settings = get_settings()
    summaries = []
    ok = True
    for index in range(max(1, int(args.repeat))):
        started = time.monotonic()
        result = worker._run_intraday_research_process_pool(
            settings,
            allow_recent_duplicates=args.allow_recent_duplicates,
        )
        elapsed = time.monotonic() - started
        summary = _summary(result, elapsed)
        summary["iteration"] = index + 1
        summary["report_artifact_mode"] = os.environ.get(_BENCHMARK_REPORT_MODE_ENV, "full")
        summaries.append(summary)
        ok = ok and result.get("status") in {"ok", "degraded"} and summary["valid"]
        if index + 1 < max(1, int(args.repeat)) and args.sleep_between > 0:
            time.sleep(float(args.sleep_between))
    print(json.dumps({"runs": summaries}, indent=2, sort_keys=True))
    return 0 if ok else 1


def _summary(result: dict[str, Any], elapsed: float) -> dict[str, Any]:
    details = result.get("details") or {}
    runs = details.get("runs") or []
    worker_results = _worker_results(details.get("worker_results"))
    process_workers = _optional_int(details.get("process_workers")) or 0
    summary = {
        "status": result.get("status"),
        "reason": result.get("reason"),
        "elapsed_wall_s": round(elapsed, 3),
        "details_elapsed_s": details.get("elapsed_seconds"),
        "runs": len(runs),
        "process_start_method": details.get("process_start_method"),
        "allow_recent_duplicates": details.get("allow_recent_duplicates"),
        "windows": sum(int(run.get("windows_sampled") or 0) for run in runs),
        "clusters": sum(int(run.get("clusters_evaluated") or 0) for run in runs),
        "accepted": sum(int(run.get("accepted_patterns") or 0) for run in runs),
        "rejected": sum(int(run.get("rejected_patterns") or 0) for run in runs),
        "errors": details.get("errors") or [],
        "skipped": len(details.get("skipped") or []),
        "worker_tail": _worker_tail_summary(worker_results, elapsed, process_workers),
        "worker_results": worker_results,
    }
    invalid_reason = _invalid_benchmark_reason(summary)
    summary["valid"] = invalid_reason is None
    if invalid_reason is not None:
        summary["invalid_reason"] = invalid_reason
    run_diagnostics = _discovery_run_diagnostics(_run_ids(runs))
    if run_diagnostics:
        summary["discovery_run_diagnostics"] = run_diagnostics
    return summary


def _invalid_benchmark_reason(summary: dict[str, Any]) -> str | None:
    if int(summary.get("runs") or 0) <= 0:
        return "no_discovery_runs"
    if int(summary.get("windows") or 0) <= 0:
        return "zero_windows"
    if int(summary.get("clusters") or 0) <= 0:
        return "zero_clusters"
    return None


def _run_ids(runs: list[Any]) -> list[int]:
    run_ids: list[int] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        run_id = _optional_int(run.get("run_id"))
        if run_id is not None:
            run_ids.append(run_id)
    return run_ids


def _discovery_run_diagnostics(run_ids: list[int]) -> dict[str, Any]:
    if not run_ids:
        return {}
    try:
        from tradeo.db.models import DiscoveryRun
        from tradeo.db.session import SessionLocal
    except Exception as exc:  # noqa: BLE001
        return {"error": f"diagnostics_import_failed: {type(exc).__name__}: {exc}"}

    db = SessionLocal()
    try:
        rows = (
            db.query(DiscoveryRun)
            .filter(DiscoveryRun.id.in_(run_ids))
            .order_by(DiscoveryRun.id)
            .all()
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"diagnostics_query_failed: {type(exc).__name__}: {exc}"}
    finally:
        db.close()

    phase_values: dict[str, list[float]] = {}
    profile_buckets: dict[str, int] = {}
    profile_frames: dict[tuple[str, str, int, str], int] = {}
    profiled_runs = 0
    for row in rows:
        summary = row.summary_json if isinstance(row.summary_json, dict) else {}
        for phase, value in _phase_timings(summary).items():
            phase_values.setdefault(phase, []).append(value)
        profile = _clustering_profile(summary)
        if not profile:
            continue
        profiled_runs += 1
        for bucket in profile.get("buckets") or []:
            if not isinstance(bucket, dict):
                continue
            name = str(bucket.get("bucket") or "unknown")
            profile_buckets[name] = profile_buckets.get(name, 0) + int(
                _optional_int(bucket.get("samples")) or 0
            )
        for frame in profile.get("top_frames") or []:
            if not isinstance(frame, dict):
                continue
            key = (
                str(frame.get("filename") or ""),
                str(frame.get("function") or ""),
                int(_optional_int(frame.get("line")) or 0),
                str(frame.get("bucket") or "unknown"),
            )
            profile_frames[key] = profile_frames.get(key, 0) + int(
                _optional_int(frame.get("samples")) or 0
            )

    total_bucket_samples = sum(profile_buckets.values())
    diagnostics: dict[str, Any] = {
        "run_ids": [int(run_id) for run_id in run_ids],
        "phase_summary": {
            phase: {
                "runs": len(values),
                "avg_s": _rounded(mean(values)),
                "max_s": _rounded(max(values)),
                "total_s": _rounded(sum(values)),
            }
            for phase, values in sorted(phase_values.items())
        },
    }
    if profiled_runs:
        diagnostics["clustering_profile"] = {
            "profiled_runs": profiled_runs,
            "samples": int(total_bucket_samples),
            "buckets": [
                {
                    "bucket": bucket,
                    "samples": int(samples),
                    "sample_pct": _rounded((samples / max(total_bucket_samples, 1)) * 100.0),
                }
                for bucket, samples in sorted(
                    profile_buckets.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "top_frames": [
                {
                    "filename": key[0],
                    "function": key[1],
                    "line": key[2],
                    "bucket": key[3],
                    "samples": int(samples),
                    "sample_pct": _rounded((samples / max(total_bucket_samples, 1)) * 100.0),
                }
                for key, samples in sorted(
                    profile_frames.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:12]
            ],
        }
    return diagnostics


def _phase_timings(summary: Any) -> dict[str, float]:
    if not isinstance(summary, dict):
        return {}
    timings = summary.get("phase_timings")
    if not isinstance(timings, dict):
        return {}
    output: dict[str, float] = {}
    for key, value in timings.items():
        parsed = _optional_float(value)
        if parsed is not None:
            output[str(key)] = parsed
    return output


def _clustering_profile(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    diagnostics = summary.get("phase_diagnostics")
    if not isinstance(diagnostics, dict):
        return {}
    profile = diagnostics.get("clustering_profile")
    return profile if isinstance(profile, dict) else {}


def _worker_results(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _worker_tail_summary(
    worker_results: list[dict[str, Any]],
    elapsed_wall_s: float,
    process_workers: int,
) -> dict[str, Any]:
    rows = [row for row in worker_results if _optional_float(row.get("elapsed_seconds")) is not None]
    if not rows:
        return {}

    elapsed_values = [_optional_float(row.get("elapsed_seconds")) or 0.0 for row in rows]
    total_worker_s = sum(elapsed_values)
    avg_worker_s = mean(elapsed_values)
    max_worker_s = max(elapsed_values)
    min_worker_s = min(elapsed_values)
    effective_workers = max(1, min(int(process_workers or 1), len(rows)))
    capacity_s = max(elapsed_wall_s, 0.001) * effective_workers
    by_timeframe = []
    for timeframe in sorted({str(row.get("timeframe") or "") for row in rows}):
        timeframe_rows = [row for row in rows if str(row.get("timeframe") or "") == timeframe]
        timeframe_elapsed = [
            _optional_float(row.get("elapsed_seconds")) or 0.0 for row in timeframe_rows
        ]
        by_timeframe.append(
            {
                "timeframe": timeframe,
                "workers": len(timeframe_rows),
                "total_worker_s": _rounded(sum(timeframe_elapsed)),
                "avg_worker_s": _rounded(mean(timeframe_elapsed)),
                "max_worker_s": _rounded(max(timeframe_elapsed)),
            }
        )

    slowest = sorted(
        rows,
        key=lambda row: (
            -(_optional_float(row.get("elapsed_seconds")) or 0.0),
            _worker_order_key(row, fallback=0),
        ),
    )[:5]
    return {
        "workers_reported": len(rows),
        "elapsed_wall_s": _rounded(elapsed_wall_s),
        "total_worker_s": _rounded(total_worker_s),
        "avg_worker_s": _rounded(avg_worker_s),
        "min_worker_s": _rounded(min_worker_s),
        "max_worker_s": _rounded(max_worker_s),
        "max_to_avg_ratio": _rounded(max_worker_s / avg_worker_s) if avg_worker_s > 0 else None,
        "pool_utilization_pct": _rounded((total_worker_s / capacity_s) * 100.0),
        "wall_minus_max_worker_s": _rounded(elapsed_wall_s - max_worker_s),
        "by_timeframe": by_timeframe,
        "slowest_workers": [_worker_brief(row) for row in slowest],
        "estimated_queue": _estimated_worker_queue(rows, effective_workers),
    }


def _estimated_worker_queue(
    worker_results: list[dict[str, Any]],
    process_workers: int,
) -> dict[str, Any]:
    if not worker_results:
        return {}

    ordered = sorted(
        enumerate(worker_results),
        key=lambda item: _worker_order_key(item[1], fallback=item[0]),
    )
    worker_count = max(1, min(int(process_workers or 1), len(ordered)))
    slot_available = [0.0 for _ in range(worker_count)]
    slot_jobs: list[list[dict[str, Any]]] = [[] for _ in range(worker_count)]
    scheduled: list[dict[str, Any]] = []
    for _, row in ordered:
        slot = min(range(worker_count), key=lambda index: (slot_available[index], index))
        started = slot_available[slot]
        duration = _optional_float(row.get("elapsed_seconds")) or 0.0
        finished = started + duration
        slot_available[slot] = finished
        item = {
            **_worker_brief(row),
            "slot": slot,
            "estimated_start_s": _rounded(started),
            "estimated_finish_s": _rounded(finished),
        }
        slot_jobs[slot].append(item)
        scheduled.append(item)

    critical_slot = max(range(worker_count), key=lambda index: (slot_available[index], -index))
    final_start_s = max(item["estimated_start_s"] for item in scheduled)
    final_wave_jobs = [
        item for item in scheduled if abs(float(item["estimated_start_s"]) - final_start_s) < 0.001
    ]
    return {
        "workers": worker_count,
        "estimated_makespan_s": _rounded(max(slot_available)),
        "estimated_queue_wait_tail_s": _rounded(final_start_s),
        "critical_slot": critical_slot,
        "critical_path": slot_jobs[critical_slot],
        "final_wave_jobs": final_wave_jobs,
    }


def _worker_brief(row: dict[str, Any]) -> dict[str, Any]:
    chunk_number = _optional_int(row.get("chunk_number"))
    chunk_count = _optional_int(row.get("chunk_count"))
    return {
        "timeframe": row.get("timeframe"),
        "chunk": (
            f"{chunk_number}_of_{chunk_count}"
            if chunk_number is not None and chunk_count is not None
            else None
        ),
        "symbols": _optional_int(row.get("symbols")),
        "estimated_cost": _optional_int(row.get("estimated_cost")),
        "elapsed_seconds": _rounded(_optional_float(row.get("elapsed_seconds")) or 0.0),
        "submitted_order": _optional_int(row.get("submitted_order")),
        "completed_order": _optional_int(row.get("completed_order")),
    }


def _worker_order_key(row: dict[str, Any], *, fallback: int) -> tuple[int, str, int]:
    submitted_order = _optional_int(row.get("submitted_order"))
    chunk_index = _optional_int(row.get("chunk_index")) or 0
    return (
        submitted_order if submitted_order is not None else fallback,
        str(row.get("timeframe") or ""),
        chunk_index,
    )


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _rounded(value: float) -> float:
    return round(float(value), 3)


if __name__ == "__main__":
    raise SystemExit(main())
