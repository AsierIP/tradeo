#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradeo.research.intraday_vwap_research import analyze_intraday_vwap_research, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze cached intraday OHLCV for read-only VWAP research context.")
    parser.add_argument("--ohlcv-cache-dir", required=True)
    parser.add_argument("--universe-file", required=True)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--period", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--forensics-json", default=None)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--md-out", default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    try:
        summary = analyze_intraday_vwap_research(
            ohlcv_cache_dir=args.ohlcv_cache_dir,
            universe_file=args.universe_file,
            limit=args.limit,
            period=args.period,
            timeframe=args.timeframe,
            forensics_json=args.forensics_json,
        )
    except (OSError, ValueError) as exc:
        summary = {
            "schema_version": "tradeo.intraday_vwap_research.v1",
            "status": "NOT_AVAILABLE",
            "error": str(exc),
            "universe": {
                "path": args.universe_file,
                "limit": args.limit,
                "symbols_requested": 0,
                "symbols_analyzed": 0,
                "missing_symbols": [],
            },
            "vwap_summary": {
                "bars_analyzed": 0,
                "above_vwap_pct": None,
                "below_vwap_pct": None,
                "median_distance_bps": None,
                "p90_abs_distance_bps": None,
                "vwap_crosses_per_symbol_median": None,
                "vwap_chop_rate": None,
            },
            "session_bucket_stats": {},
            "symbol_stats": [],
            "candidate_search_spaces": [],
            "recommended_next_waves": [],
            "blocked_waves": [],
            "safety": {
                "live_allowed": False,
                "paper_allowed": False,
                "orders_allowed": False,
                "ibkr_used": False,
                "wave_executed": False,
            },
        }

    markdown = render_markdown(summary)
    if args.json_out:
        json_out = Path(args.json_out)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if args.md_out:
        md_out = Path(args.md_out)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(markdown, encoding="utf-8")

    if args.json_only:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(markdown)
        print("JSON:")
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
