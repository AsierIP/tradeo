#!/usr/bin/env python3
"""Validate DSS-003 Daily OHLCV cache quality."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from tradeo.modules.daily_swing.dss_003 import CacheResult, check_daily_ohlcv_quality, write_dss_003_reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default="artifacts/runtime/daily_swing/daily_ohlcv")
    parser.add_argument("--universe", default="artifacts/runtime/daily_swing/dss_003_universe_pilot.csv")
    parser.add_argument("--end-date", default="2026-07-06")
    parser.add_argument("--report-csv", default="artifacts/runtime/daily_swing/dss_003_daily_quality_report.csv")
    parser.add_argument("--summary-json", default="artifacts/runtime/daily_swing/dss_003_daily_quality_summary.json")
    parser.add_argument("--min-operational-ready", type=int, default=50)
    parser.add_argument("--cache-status", default="NOT_RUN")
    parser.add_argument("--cache-error", default=None)
    parser.add_argument("--write-reports", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    summary = check_daily_ohlcv_quality(
        cache_dir=Path(args.cache_dir),
        universe_path=Path(args.universe),
        end_date=args.end_date,
        report_csv=Path(args.report_csv),
        summary_json=Path(args.summary_json),
        min_operational_ready=args.min_operational_ready,
    )
    if args.write_reports:
        manifest_path = Path("artifacts/runtime/daily_swing/dss_003_daily_cache_manifest.json")
        manifest = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        write_dss_003_reports(
            None,
            CacheResult(
                args.cache_status,
                int(manifest.get("fetched", 0) or 0),
                int(manifest.get("skipped", 0) or 0),
                int(manifest.get("failed", 0) or 0),
                manifest_path,
                args.cache_error or manifest.get("error"),
            ),
            summary,
        )
    if not args.json_only:
        print(f"daily quality data_gate={summary['data_gate']} operational_ready={summary['operational_ready']}")
        print("JSON:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["data_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
