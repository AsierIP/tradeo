#!/usr/bin/env python3
"""Probe IBKR API handshake and tiny historical canaries in read-only mode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.core.config import get_settings
from tradeo.services.ibkr_data_provider import _bar_size_from_interval, _duration_from_period, _ensure_event_loop

from diagnose_ibkr_connectivity import classify_port


def validate_readonly_api_probe_settings(settings: Any) -> tuple[bool, str]:
    if not bool(settings.ibkr_readonly):
        return False, "read_only=false"
    classification = classify_port(int(settings.ibkr_port))
    if classification == "LIVE_PORT_RISK":
        return False, "live_port_risk"
    if classification == "AMBIGUOUS_PORT":
        return False, "ambiguous_port"
    return True, classification


def _connect_once(settings: Any, client_id: int):
    _ensure_event_loop()
    from ib_insync import IB

    ib = IB()
    ib.connect(
        settings.ibkr_host,
        settings.ibkr_port,
        clientId=client_id,
        timeout=float(getattr(settings, "ibkr_connect_timeout_seconds", 8.0)),
    )
    return ib


def run_handshake_probe(settings: Any, client_id: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_id": client_id,
        "connected": False,
        "status": "FAILED",
        "orders_used": False,
        "paper_orders_used": False,
        "live_used": False,
        "account_data_used": False,
        "historical_data_used": False,
    }
    ib = None
    try:
        ib = _connect_once(settings, client_id)
        payload.update(
            {
                "connected": bool(ib.isConnected()),
                "server_version": ib.client.serverVersion() if ib.client else None,
                "status": "OK" if ib.isConnected() else "FAILED",
            }
        )
    except Exception as exc:  # noqa: BLE001 - ib_insync connection errors are heterogeneous.
        payload["error"] = str(exc)
    finally:
        if ib and ib.isConnected():
            ib.disconnect()
    return payload


def run_historical_canary(settings: Any, client_id: int, symbol: str, period: str, timeout: float) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_id": client_id,
        "symbol": symbol.upper(),
        "period": period,
        "interval": "1d",
        "connected": False,
        "historical_data_ok": False,
        "bars_count": 0,
        "status": "FAILED",
        "orders_used": False,
        "paper_orders_used": False,
        "live_used": False,
        "account_data_used": False,
    }
    ib = None
    try:
        from ib_insync import Stock, util

        ib = _connect_once(settings, client_id)
        payload["connected"] = bool(ib.isConnected())
        contract = Stock(symbol.upper(), "SMART", "USD")
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            raise ValueError(f"IBKR could not qualify contract for {symbol}")
        bars = ib.reqHistoricalData(
            qualified[0],
            endDateTime="",
            durationStr=_duration_from_period(period),
            barSizeSetting=_bar_size_from_interval("1d"),
            whatToShow=settings.market_data_what_to_show,
            useRTH=True,
            formatDate=1,
            timeout=timeout,
        )
        frame = util.df(bars)
        bars_count = 0 if frame is None else int(len(frame))
        payload.update(
            {
                "historical_data_ok": bars_count > 0,
                "bars_count": bars_count,
                "last_bar_date": str(frame["date"].max()) if frame is not None and not frame.empty else None,
                "status": "OK" if bars_count > 0 else "FAILED",
            }
        )
    except Exception as exc:  # noqa: BLE001 - IBKR request errors are heterogeneous.
        payload["error"] = str(exc)
    finally:
        if ib and ib.isConnected():
            ib.disconnect()
    return payload


def classify_probe_result(handshakes: list[dict[str, Any]], historical: list[dict[str, Any]]) -> str:
    handshake_ok = any(item.get("connected") and item.get("status") == "OK" for item in handshakes)
    historical_ok = all(item.get("historical_data_ok") for item in historical) if historical else False
    if not handshake_ok:
        return "API_HANDSHAKE_FAIL"
    if not historical_ok:
        return "HISTORICAL_CANARY_FAIL"
    return "API_HISTORICAL_READY"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-ids", nargs="+", type=int, default=[17, 117, 217])
    parser.add_argument("--canary", action="append", default=None)
    parser.add_argument("--historical-timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    settings = get_settings()
    allowed, reason = validate_readonly_api_probe_settings(settings)
    payload: dict[str, Any] = {
        "host": settings.ibkr_host,
        "port": settings.ibkr_port,
        "read_only": settings.ibkr_readonly,
        "port_classification": reason,
        "orders_used": False,
        "paper_orders_used": False,
        "live_used": False,
        "account_data_used": False,
        "research_cache_used": False,
        "handshakes": [],
        "historical_canaries": [],
    }
    if not allowed:
        payload.update({"decision": "BLOCKED", "block_reason": reason})
    else:
        payload["handshakes"] = [run_handshake_probe(settings, client_id) for client_id in args.client_ids]
        historical_client_id = next(
            (item["client_id"] for item in payload["handshakes"] if item.get("connected") and item.get("status") == "OK"),
            args.client_ids[0],
        )
        for spec in args.canary or ["SPY:5D", "AAON:5D"]:
            symbol, _, period = spec.partition(":")
            payload["historical_canaries"].append(
                run_historical_canary(settings, historical_client_id, symbol, period or "5D", args.historical_timeout)
            )
        payload["decision"] = classify_probe_result(payload["handshakes"], payload["historical_canaries"])

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload.get("decision") == "API_HISTORICAL_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
