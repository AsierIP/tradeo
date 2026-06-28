#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from tradeo.core.config import get_settings
from tradeo.services.intraday_universe_builder import (
    IntradayUniverseBuilder,
    IntradayUniverseThresholds,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a liquid intraday Tradeo universe CSV.")
    parser.add_argument(
        "--seed-file",
        action="append",
        default=[],
        help="Candidate CSV with a symbol column. Can be repeated.",
    )
    parser.add_argument("--output", default="/app/artifacts/runtime/universe_intraday_liquid.csv")
    parser.add_argument("--period", default="60d")
    parser.add_argument("--interval", default="30m")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--refresh", action="store_true", help="Allow provider refresh/miss-fill while scoring.")
    parser.add_argument("--rotation-salt", default=None)
    parser.add_argument("--min-price", type=float, default=3.0)
    parser.add_argument("--min-median-dollar-volume", type=float, default=5_000_000.0)
    parser.add_argument("--min-rows", type=int, default=120)
    parser.add_argument("--max-zero-volume-pct", type=float, default=0.05)
    parser.add_argument("--max-stale-close-run", type=int, default=5)
    parser.add_argument("--max-spread-proxy-bps", type=float, default=450.0)
    parser.add_argument("--max-event-bar-return-pct", type=float, default=0.35)
    parser.add_argument("--max-bucket-pct", type=float, default=0.30)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    seed_files = args.seed_file or [
        "/app/data/universe_us_small_caps.csv",
        "/app/data/universe_us_mid_caps.csv",
    ]
    thresholds = IntradayUniverseThresholds(
        min_price=args.min_price,
        min_median_dollar_volume=args.min_median_dollar_volume,
        min_rows=args.min_rows,
        max_zero_volume_pct=args.max_zero_volume_pct,
        max_stale_close_run=args.max_stale_close_run,
        max_spread_proxy_bps=args.max_spread_proxy_bps,
        max_event_bar_return_pct=args.max_event_bar_return_pct,
        max_bucket_pct=args.max_bucket_pct,
    )
    result = IntradayUniverseBuilder(settings=settings).build(
        seed_files=[Path(item) for item in seed_files],
        output_path=Path(args.output),
        limit=args.limit,
        period=args.period,
        interval=args.interval,
        thresholds=thresholds,
        cache_refresh_enabled=args.refresh,
        rotation_salt=args.rotation_salt,
    )
    payload = {
        "output_path": str(result.output_path),
        "metadata_path": str(result.metadata_path),
        "selected_count": result.selected_count,
        "rejected_count": result.rejected_count,
        "total_candidates": result.total_candidates,
        "selected_preview": result.selected_symbols[:25],
        "thresholds": asdict(thresholds),
    }
    if not args.json_only:
        print(
            f"built universe selected={result.selected_count} rejected={result.rejected_count} "
            f"total={result.total_candidates} output={result.output_path}"
        )
        print("selected preview:", ",".join(result.selected_symbols[:25]))
        print("JSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.selected_count > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
