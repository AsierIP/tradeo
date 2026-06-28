#!/usr/bin/env python3
"""Fetch candidate symbols from IBKR Market Scanner for universe building.

The scanner returns contracts, not liquidity fields; run build_intraday_universe.py
after this step to score candidates with cached OHLCV quality/liquidity metrics.
This script is read-only and never submits orders.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tradeo.core.config import get_settings
from tradeo.services.ibkr_data_provider import _connect_ibkr

DEFAULT_SCAN_CODES = "HOT_BY_VOLUME,MOST_ACTIVE,TOP_PERC_GAIN,TOP_PERC_LOSE"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-codes", default=DEFAULT_SCAN_CODES)
    parser.add_argument("--location-code", default="STK.US.MAJOR")
    parser.add_argument("--instrument", default="STK")
    parser.add_argument("--rows-per-scan", type=int, default=50)
    parser.add_argument("--output", default="/app/artifacts/runtime/ibkr_intraday_scanner_candidates.csv")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    scan_codes = [item.strip().upper() for item in args.scan_codes.split(",") if item.strip()]
    rows: list[dict[str, Any]] = []
    ib = None
    try:
        ib, client_id = _connect_ibkr(settings)
        for scan_code in scan_codes:
            rows.extend(
                fetch_scan(
                    ib,
                    scan_code=scan_code,
                    instrument=args.instrument,
                    location_code=args.location_code,
                    rows_per_scan=args.rows_per_scan,
                )
            )
    finally:
        if ib is not None and ib.isConnected():
            ib.disconnect()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = (
            df.sort_values(["symbol", "scan_rank"])
            .drop_duplicates("symbol", keep="first")
            .sort_values(["scan_code", "scan_rank", "symbol"])
        )
    df.to_csv(output, index=False)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "client_id": client_id if "client_id" in locals() else None,
        "scan_codes": scan_codes,
        "instrument": args.instrument,
        "location_code": args.location_code,
        "rows_per_scan": args.rows_per_scan,
        "output": str(output),
        "candidates": int(len(df)),
        "note": "IBKR scanner returns contracts only; score liquidity with build_intraday_universe.py",
    }
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    if not args.json_only:
        print(f"scanner candidates={len(df)} output={output}")
        print("JSON:")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0 if len(df) else 2


def fetch_scan(
    ib: Any,
    *,
    scan_code: str,
    instrument: str,
    location_code: str,
    rows_per_scan: int,
) -> list[dict[str, Any]]:
    from ib_insync import ScannerSubscription

    scan = ScannerSubscription()
    scan.instrument = instrument
    scan.locationCode = location_code
    scan.scanCode = scan_code
    scan.numberOfRows = int(rows_per_scan)
    results = ib.reqScannerData(scan, [], [])
    rows: list[dict[str, Any]] = []
    for item in results:
        contract_details = getattr(item, "contractDetails", None)
        contract = getattr(contract_details, "contract", None)
        if contract is None:
            continue
        symbol = str(getattr(contract, "symbol", "") or "").upper().strip()
        if not symbol:
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": str(getattr(contract_details, "longName", "") or ""),
                "cap_segment": "scanner",
                "sector": "",
                "note": f"ibkr_scanner:{scan_code}",
                "scan_code": scan_code,
                "scan_rank": int(getattr(item, "rank", len(rows) + 1) or len(rows) + 1),
                "con_id": int(getattr(contract, "conId", 0) or 0),
                "primary_exchange": str(getattr(contract, "primaryExchange", "") or ""),
                "currency": str(getattr(contract, "currency", "") or ""),
            }
        )
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
