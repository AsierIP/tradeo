#!/usr/bin/env python3
"""Probe one IBKR historical-data request in read-only, paper-port mode only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.core.config import get_settings
from tradeo.services.ibkr_data_provider import IBKRHistoricalDataProvider

from diagnose_ibkr_connectivity import classify_port


def validate_readonly_probe_settings(settings: Any) -> tuple[bool, str]:
    if not bool(settings.ibkr_readonly):
        return False, "read_only=false"
    classification = classify_port(int(settings.ibkr_port))
    if classification == "LIVE_PORT_RISK":
        return False, "live_port_risk"
    if classification == "AMBIGUOUS_PORT":
        return False, "ambiguous_port"
    return True, classification


def run_probe(symbol: str = "SPY", period: str = "5D") -> dict[str, Any]:
    settings = get_settings()
    allowed, reason = validate_readonly_probe_settings(settings)
    payload: dict[str, Any] = {
        "symbol": symbol,
        "period": period,
        "host": settings.ibkr_host,
        "port": settings.ibkr_port,
        "client_id": settings.ibkr_client_id,
        "read_only": settings.ibkr_readonly,
        "orders_used": False,
        "paper_orders_used": False,
        "live_used": False,
        "connected": False,
        "historical_data_ok": False,
        "bars_count": 0,
    }
    if not allowed:
        payload.update({"status": "BLOCKED", "block_reason": reason})
        return payload

    provider = IBKRHistoricalDataProvider(settings=settings)
    try:
        frame = provider.fetch_ohlcv(symbol.upper(), period=period.lower(), interval="1d")
    except Exception as exc:  # noqa: BLE001 - IBKR connection/provider errors are heterogeneous.
        payload.update({"status": "FAILED", "error": str(exc)})
        return payload

    payload.update(
        {
            "status": "OK",
            "connected": True,
            "historical_data_ok": not frame.empty,
            "bars_count": int(len(frame)),
            "last_bar_date": str(frame["date"].max()) if "date" in frame.columns and not frame.empty else None,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--period", default="5D")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = run_probe(args.symbol, args.period)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload.get("historical_data_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
