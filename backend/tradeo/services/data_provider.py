from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd
import yfinance as yf
from loguru import logger

from tradeo.core.config import get_settings
from tradeo.services.technical_indicators import normalize_ohlcv, seeded_synthetic_ohlcv


class MarketDataProvider(Protocol):
    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        ...


@dataclass
class YFinanceProvider:
    allow_synthetic_fallback: bool = True

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        try:
            df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
            if df is None or df.empty:
                raise ValueError("empty dataset")
            return normalize_ohlcv(df)
        except Exception as exc:  # noqa: BLE001
            logger.warning("market data fetch failed for {}: {}", symbol, exc)
            if self.allow_synthetic_fallback:
                return seeded_synthetic_ohlcv(symbol)
            raise


def load_universe(path: str | None = None) -> pd.DataFrame:
    settings = get_settings()
    p = Path(path or settings.universe_file)
    if not p.exists():
        raise FileNotFoundError(f"Universe file not found: {p}")
    df = pd.read_csv(p)
    if "symbol" not in df.columns:
        raise ValueError("Universe CSV must include a 'symbol' column")
    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    df = df[df["symbol"].str.len() > 0].drop_duplicates("symbol")
    return df


def pick_symbols(limit: int | None = None, force_symbols: list[str] | None = None) -> list[str]:
    if force_symbols:
        return [s.upper().strip() for s in force_symbols if s.strip()]
    settings = get_settings()
    df = load_universe(settings.universe_file)
    n = limit or settings.scan_limit_default
    return df["symbol"].head(n).tolist()


@dataclass
class CachedMarketDataProvider:
    upstream: MarketDataProvider | None = None

    def __post_init__(self) -> None:
        self.upstream = self.upstream or YFinanceProvider()
        self._cache: dict[tuple[str, str, str], pd.DataFrame] = {}

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        key = (symbol.upper(), period, interval)
        if key not in self._cache:
            self._cache[key] = self.upstream.fetch_ohlcv(symbol, period=period, interval=interval)
        return self._cache[key].copy()
