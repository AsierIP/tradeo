from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pandas as pd

from tradeo.core.config import Settings, get_settings
from tradeo.services.technical_indicators import normalize_ohlcv


def _duration_from_period(period: str) -> str:
    p = period.lower().strip()
    if p.endswith("y"):
        return f"{int(p[:-1])} Y"
    if p.endswith("mo"):
        return f"{int(p[:-2])} M"
    if p.endswith("d"):
        return f"{int(p[:-1])} D"
    return "2 Y"


def _bar_size_from_interval(interval: str) -> str:
    mapping = {
        "1d": "1 day",
        "1wk": "1 week",
        "1h": "1 hour",
        "30m": "30 mins",
        "15m": "15 mins",
        "5m": "5 mins",
        "1m": "1 min",
    }
    return mapping.get(interval.lower(), "1 day")


def _ensure_event_loop() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


@dataclass
class IBKRHistoricalDataProvider:
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        _ensure_event_loop()
        from ib_insync import IB, Stock, util

        ib = IB()
        ib.connect(
            self.settings.ibkr_host,
            self.settings.ibkr_port,
            clientId=self.settings.ibkr_client_id,
            timeout=float(getattr(self.settings, "ibkr_connect_timeout_seconds", 8.0)),
        )
        try:
            contract = Stock(symbol.upper(), "SMART", "USD")
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                raise ValueError(f"IBKR could not qualify contract for {symbol}")
            contract = qualified[0]
            bars = ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=_duration_from_period(period),
                barSizeSetting=_bar_size_from_interval(interval),
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            df = util.df(bars)
            if df is None or df.empty:
                raise ValueError(f"IBKR returned no bars for {symbol}")
            if "date" in df.columns:
                df = df.set_index("date")
            return normalize_ohlcv(df)
        finally:
            ib.disconnect()


def inspect_ibkr_connection(settings: Settings | None = None) -> dict[str, Any]:
    """Read-only connectivity check for TWS/IB Gateway.

    This function is safe for public health endpoints: it confirms connectivity but does not
    return balances or managed account identifiers. Use the admin-only IBKR account endpoint
    for detailed account state.
    """
    settings = settings or get_settings()
    _ensure_event_loop()
    from ib_insync import IB

    ib = IB()
    try:
        ib.connect(
            settings.ibkr_host,
            settings.ibkr_port,
            clientId=settings.ibkr_client_id,
            timeout=float(getattr(settings, "ibkr_connect_timeout_seconds", 8.0)),
        )
        server_time = ib.reqCurrentTime()
        managed_accounts = ib.managedAccounts()
        return {
            "ok": True,
            "host": settings.ibkr_host,
            "port": settings.ibkr_port,
            "client_id": settings.ibkr_client_id,
            "readonly": settings.ibkr_readonly,
            "trading_mode": settings.trading_mode,
            "live_armed": settings.live_armed,
            "server_time": server_time.isoformat(),
            "managed_accounts_count": len(managed_accounts),
            "selected_account_configured": bool(settings.ibkr_account),
            "account_summary_included": False,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "host": settings.ibkr_host,
            "port": settings.ibkr_port,
            "client_id": settings.ibkr_client_id,
            "readonly": settings.ibkr_readonly,
            "trading_mode": settings.trading_mode,
            "live_armed": settings.live_armed,
            "error": str(exc),
        }
    finally:
        if ib.isConnected():
            ib.disconnect()
