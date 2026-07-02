#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.laboratory.vwap_shadow_recorder import (  # noqa: E402
    ShadowQuote,
    build_vwap_shadow_record,
    write_shadow_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one read-only VWAP Lab shadow smoke record.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--side", required=True, choices=("long", "short"))
    parser.add_argument("--vwap-condition", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    parser.add_argument("--bid", type=float)
    parser.add_argument("--ask", type=float)
    parser.add_argument("--last", type=float)
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

    quote = ShadowQuote(bid=args.bid, ask=args.ask, last=args.last, source="cli_safe_mock")
    record = build_vwap_shadow_record(
        symbol=args.symbol,
        side=args.side,
        vwap_condition=args.vwap_condition,
        timeframe=args.timeframe,
        quote=quote,
        market_open=market_open,
    )
    write_shadow_artifacts(record, json_out=args.json_out, md_out=args.md_out)
    print(json.dumps(record, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
