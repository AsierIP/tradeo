#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any

from tradeo.core.config import get_settings
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
        result = worker._run_intraday_research_process_pool(
            settings,
            allow_recent_duplicates=bool(args.allow_recent_duplicates),
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
    manifest_path.write_text(json.dumps(wave_result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    summary = {
        "decision": wave_result["decision"],
        "manifest_path": str(manifest_path),
        "ready": readiness.ready,
        "coverage": readiness.coverage,
        "ok": readiness.ok,
        "total": readiness.total,
        "execute": bool(args.execute),
        "research_status": (wave_result.get("research_result") or {}).get("status"),
    }
    if not args.json_only:
        print(
            f"decision={summary['decision']} ready={summary['ready']} "
            f"coverage={summary['coverage']:.2%} ok={summary['ok']}/{summary['total']} "
            f"manifest={manifest_path}"
        )
        print("JSON:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return status_code


def _csv_str(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _csv_int(raw: str) -> list[int]:
    return [int(item.strip()) for item in str(raw).split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
