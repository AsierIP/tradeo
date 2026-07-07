#!/usr/bin/env python3
"""Cache Daily OHLCV bars for DSS-003.

Read-only only. This script never submits orders and refuses to run unless
`--read-only` is passed and settings keep IBKR in read-only mode.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from tradeo.core.config import get_settings
from tradeo.modules.daily_swing.dss_003 import build_daily_universes, cache_daily_ohlcv
from tradeo.modules.resource_policy.enforcement import blocked_job_status, decide_with_market_session_policy
from tradeo.modules.resource_policy.market_session_resource_policy import JobType


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", default="artifacts/runtime/daily_swing/dss_003_universe_smoke.csv")
    parser.add_argument("--out-dir", default="artifacts/runtime/daily_swing/daily_ohlcv")
    parser.add_argument("--duration", default="3Y")
    parser.add_argument("--end-date", default="2026-07-06")
    parser.add_argument("--source", default="ibkr")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-new-fetches", type=int, default=None)
    parser.add_argument("--max-consecutive-timeouts", type=int, default=None)
    parser.add_argument("--request-timeout", type=float, default=None)
    parser.add_argument("--retry-count", type=int, default=0)
    parser.add_argument("--retry-backoff-seconds", type=float, default=0.0)
    parser.add_argument("--quarantine-failures", action="store_true")
    parser.add_argument("--continue-on-symbol-timeout", action="store_true")
    parser.add_argument("--stop-on-global-timeout", action="store_true")
    parser.add_argument("--build-universes", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    policy_decision = decide_with_market_session_policy(
        JobType.RESEARCH_HEAVY,
        "research",
        settings=get_settings(),
    )
    if not policy_decision.allowed:
        payload = {
            "decision": "blocked_resource_policy",
            "resource_policy": policy_decision.to_dict(),
            "research_result": blocked_job_status(policy_decision),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 5

    if args.build_universes:
        build_daily_universes()
    result = cache_daily_ohlcv(
        universe_path=Path(args.universe),
        out_dir=Path(args.out_dir),
        duration=args.duration,
        end_date=args.end_date,
        source=args.source,
        read_only=args.read_only,
        limit=args.limit,
        resume=args.resume,
        sleep_seconds=args.sleep,
        dry_run=args.dry_run,
        force=args.force,
        max_new_fetches=args.max_new_fetches,
        max_consecutive_timeouts=args.max_consecutive_timeouts,
        request_timeout=args.request_timeout,
        retry_count=args.retry_count,
        retry_backoff_seconds=args.retry_backoff_seconds,
        quarantine_failures=args.quarantine_failures,
        continue_on_symbol_timeout=args.continue_on_symbol_timeout,
        stop_on_global_timeout=args.stop_on_global_timeout,
    )
    payload = {
        "status": result.status,
        "fetched": result.fetched,
        "skipped": result.skipped,
        "failed": result.failed,
        "manifest_path": str(result.manifest_path),
        "error": result.error,
    }
    if not args.json_only:
        print(f"daily cache status={result.status} fetched={result.fetched} skipped={result.skipped} failed={result.failed}")
        print("JSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.dry_run:
        return 0 if result.status == "DRY_RUN_OK" else 2
    return 0 if result.status == "CACHE_WRITTEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
