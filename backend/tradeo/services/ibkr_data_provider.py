from __future__ import annotations

from dataclasses import dataclass

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


@dataclass
class IBKRHistoricalDataProvider:
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        from ib_insync import IB, Stock, util

        ib = IB()
        ib.connect(self.settings.ibkr_host, self.settings.ibkr_port, clientId=self.settings.ibkr_client_id)
        try:
            contract = Stock(symbol.upper(), "SMART", "USD")
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
