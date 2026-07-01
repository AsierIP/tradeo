#!/usr/bin/env python3
"""Warm intraday OHLCV cache with retries, per-symbol timeouts and resume support.

This is a safer alternative to warming the full intraday universe through the
regular worker when IBKR/TWS intermittently resets the API connection. Each
symbol/timeframe request runs in a short-lived child process, so a hung IBKR call
cannot keep the whole warmup container alive forever.

The script does not generate patterns, does not alter validation gates and does
not trade. It only fills `TRADEO_MARKET_DATA_CACHE_DIR`.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, TimeoutError
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any

from tradeo.core.config import get_settings
from tradeo.services.data_provider import (
    UNIVERSE_POLICY_CHOICES,
    normalize_universe_policy,
    pick_symbols,
    universe_file_for_interval,
)
from tradeo.services.provider_factory import get_market_data_provider


@dataclass(frozen=True, slots=True)
class WarmupTask:
    symbol: str
    timeframe: str
    period: str


@dataclass(frozen=True, slots=True)
class WarmupResult:
    symbol: str
    timeframe: str
    period: str
    status: str
    rows: int = 0
    elapsed_s: float = 0.0
    error: str = ""
    attempt: int = 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--period", default=None, help="Override intraday research period, e.g. 30d or 60d.")
    parser.add_argument("--limit", type=int, default=None, help="Override symbol limit.")
    parser.add_argument("--universe-file", default=None, help="Override universe CSV for all timeframes.")
    parser.add_argument(
        "--product-policy",
        "--universe-policy",
        dest="product_policy",
        choices=UNIVERSE_POLICY_CHOICES,
        default=None,
        help="Universe product policy label for cache/readiness manifests. Defaults to settings.",
    )
    parser.add_argument("--timeframes", default=None, help="Comma-separated timeframes; defaults to settings.")
    parser.add_argument("--timeout-s", type=float, default=45.0, help="Hard timeout for one symbol/timeframe fetch.")
    parser.add_argument("--retries", type=int, default=2, help="Retries per task after the first attempt.")
    parser.add_argument("--sleep-s", type=float, default=1.0, help="Delay between tasks to reduce IBKR pacing/API resets.")
    parser.add_argument("--retry-sleep-s", type=float, default=5.0, help="Delay before retrying a failed task.")
    parser.add_argument("--max-failures", type=int, default=20, help="Stop after this many failed tasks; 0 disables the cap.")
    parser.add_argument("--max-tasks", type=int, default=0, help="Debug cap over task count; 0 means all tasks.")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--progress-file", default=None, help="JSONL progress file. Defaults under artifacts/runtime.")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    period = str(args.period or settings.intraday_research_period)
    limit = int(args.limit or settings.intraday_research_limit_default)
    product_policy = normalize_universe_policy(
        args.product_policy or getattr(settings, "intraday_universe_policy", "stock_only")
    )
    timeframes = [
        item.strip()
        for item in str(args.timeframes or ",".join(settings.intraday_timeframe_list)).split(",")
        if item.strip()
    ]
    progress_path = Path(
        args.progress_file
        or (settings.artifacts_path / "runtime" / f"intraday_cache_warmup_{period}.jsonl")
    )
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    tasks = _build_tasks(
        settings=settings,
        period=period,
        limit=limit,
        timeframes=timeframes,
        universe_file=args.universe_file,
        product_policy=product_policy,
    )
    if args.max_tasks and args.max_tasks > 0:
        tasks = tasks[: int(args.max_tasks)]
    done = _read_done(progress_path) if args.resume else set()
    pending = [task for task in tasks if _task_key(task) not in done]

    results: list[WarmupResult] = []
    failure_count = 0
    started = time.monotonic()
    if not args.json_only:
        print(
            "warmup start "
            f"period={period} limit={limit} timeframes={','.join(timeframes)} "
            f"product_policy={product_policy} tasks={len(tasks)} pending={len(pending)} "
            f"cache={settings.market_data_cache_path}"
        )

    for task in pending:
        result = _run_with_retries(
            task,
            timeout_s=float(args.timeout_s),
            retries=max(0, int(args.retries)),
            retry_sleep_s=max(0.0, float(args.retry_sleep_s)),
        )
        results.append(result)
        _append_progress(progress_path, result)
        if not args.json_only:
            print(
                f"{result.status:7s} {result.symbol:8s} {result.timeframe:4s} "
                f"rows={result.rows:5d} attempt={result.attempt} elapsed={result.elapsed_s:.2f}s "
                f"{result.error[:160]}"
            )
        if result.status != "ok":
            failure_count += 1
            if int(args.max_failures or 0) > 0 and failure_count >= int(args.max_failures):
                break
        if float(args.sleep_s) > 0:
            time.sleep(float(args.sleep_s))

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "limit": limit,
        "product_policy": product_policy,
        "universe_file": args.universe_file,
        "timeframes": timeframes,
        "cache_dir": str(settings.market_data_cache_path),
        "progress_file": str(progress_path),
        "tasks_total": len(tasks),
        "tasks_already_done": len(done),
        "tasks_attempted": len(results),
        "ok": sum(1 for result in results if result.status == "ok"),
        "failed": sum(1 for result in results if result.status != "ok"),
        "elapsed_s": round(time.monotonic() - started, 3),
        "failures_by_error": _failure_counts(results),
    }
    if not args.json_only:
        print("summary:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["failed"] == 0 else 2


def _build_tasks(
    *,
    settings: Any,
    period: str,
    limit: int,
    timeframes: list[str],
    universe_file: str | None = None,
    product_policy: str = "stock_only",
) -> list[WarmupTask]:
    tasks: list[WarmupTask] = []
    for timeframe in timeframes:
        symbols = pick_symbols(
            limit=limit,
            interval=timeframe,
            universe_file=universe_file
            or universe_file_for_interval(settings, timeframe, universe_policy=product_policy),
            universe_policy=product_policy,
        )
        for symbol in symbols:
            tasks.append(WarmupTask(symbol=str(symbol).upper(), timeframe=timeframe, period=period))
    return tasks


def _run_with_retries(
    task: WarmupTask,
    *,
    timeout_s: float,
    retries: int,
    retry_sleep_s: float,
) -> WarmupResult:
    attempts = retries + 1
    last = WarmupResult(task.symbol, task.timeframe, task.period, status="failed", error="not_started")
    for attempt in range(1, attempts + 1):
        last = _run_one_with_timeout(task, timeout_s=timeout_s, attempt=attempt)
        if last.status == "ok":
            return last
        if attempt < attempts and retry_sleep_s > 0:
            time.sleep(retry_sleep_s)
    return last


def _run_one_with_timeout(task: WarmupTask, *, timeout_s: float, attempt: int) -> WarmupResult:
    with ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_fetch_one, asdict(task), attempt)
        try:
            return future.result(timeout=max(1.0, float(timeout_s)))
        except TimeoutError:
            future.cancel()
            return WarmupResult(
                symbol=task.symbol,
                timeframe=task.timeframe,
                period=task.period,
                status="timeout",
                elapsed_s=round(float(timeout_s), 3),
                error=f"timeout>{timeout_s:g}s",
                attempt=attempt,
            )


def _fetch_one(payload: dict[str, str], attempt: int) -> WarmupResult:
    started = time.monotonic()
    symbol = str(payload["symbol"])
    timeframe = str(payload["timeframe"])
    period = str(payload["period"])
    try:
        # Always refresh/miss-fill here; this script exists specifically to warm cache.
        provider = get_market_data_provider(cache_refresh_enabled=True)
        df = provider.fetch_ohlcv(symbol, period=period, interval=timeframe)
        return WarmupResult(
            symbol=symbol,
            timeframe=timeframe,
            period=period,
            status="ok",
            rows=int(len(df)),
            elapsed_s=round(time.monotonic() - started, 3),
            attempt=attempt,
        )
    except Exception as exc:  # noqa: BLE001 - diagnostic script reports provider instability.
        return WarmupResult(
            symbol=symbol,
            timeframe=timeframe,
            period=period,
            status="failed",
            elapsed_s=round(time.monotonic() - started, 3),
            error=f"{type(exc).__name__}: {exc}",
            attempt=attempt,
        )


def _task_key(task: WarmupTask) -> str:
    return f"{task.symbol}|{task.timeframe}|{task.period}"


def _result_key(result: WarmupResult) -> str:
    return f"{result.symbol}|{result.timeframe}|{result.period}"


def _read_done(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("status") == "ok":
            done.add(
                f"{str(payload.get('symbol') or '').upper()}|"
                f"{payload.get('timeframe')}|{payload.get('period')}"
            )
    return done


def _append_progress(path: Path, result: WarmupResult) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(result), sort_keys=True) + "\n")


def _failure_counts(results: list[WarmupResult]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        if result.status == "ok":
            continue
        key = result.error.split(":", 1)[0] if result.error else result.status
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


if __name__ == "__main__":
    raise SystemExit(main())
