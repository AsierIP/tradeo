#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.laboratory.vwap_shadow_runner import (  # noqa: E402
    ShadowBatchRequest,
    load_symbols,
    run_shadow_batch,
    write_shadow_batch_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only VWAP Lab shadow records for a symbol batch.")
    parser.add_argument("--symbols")
    parser.add_argument("--universe-file")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--vwap-condition", required=True)
    parser.add_argument("--side", required=True, choices=("long", "short"))
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--jsonl-out", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--summary-md", required=True)
    parser.add_argument("--market-open", action="store_true", help="Force market-open classification for tests/smoke.")
    parser.add_argument("--market-closed", action="store_true", help="Force market-closed classification for tests/smoke.")
    args = parser.parse_args()

    market_open = None
    if args.market_open and args.market_closed:
        parser.error("--market-open and --market-closed are mutually exclusive")
    if args.market_open:
        market_open = True
    if args.market_closed:
        market_open = False
    symbols = load_symbols(symbols=args.symbols, universe_file=args.universe_file, limit=args.limit)
    if not symbols:
        parser.error("provide --symbols or --universe-file with at least one symbol")

    request = ShadowBatchRequest(
        symbols=tuple(symbols),
        side=args.side,
        vwap_condition=args.vwap_condition,
        timeframe=args.timeframe,
        market_open=market_open,
    )
    records, summary = run_shadow_batch(request)
    write_shadow_batch_artifacts(
        records,
        summary,
        jsonl_out=args.jsonl_out,
        summary_json=args.summary_json,
        summary_md=args.summary_md,
    )
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 1 if summary["forbidden_outcomes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
