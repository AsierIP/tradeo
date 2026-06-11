from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import blake2b
import math
from typing import Any

import numpy as np
import pandas as pd

from tradeo.core.config import Settings, get_settings
from tradeo.services.data_provider import MarketDataProvider
from tradeo.services.technical_indicators import normalize_ohlcv

TREND_BULL = "benchmark_bull"
TREND_BEAR = "benchmark_bear"
VOL_TERCILE_LABELS = ("low_vol_tercile", "mid_vol_tercile", "high_vol_tercile")
INSUFFICIENT_HISTORY = "insufficient_history"

TRADING_DAYS_PER_YEAR = 252


def regime_table(
    df: pd.DataFrame,
    *,
    sma_window: int = 200,
    vol_window: int = 20,
    tercile_lookback: int = 252,
) -> pd.DataFrame:
    """Per-bar benchmark regime labels from closed daily bars only.

    Trend: close vs strict SMA(sma_window) (full window required, no partial
    min_periods so a young series never pretends to know its 200-day trend).
    Volatility: annualized stdev of log returns over vol_window, bucketed into
    terciles whose boundaries come exclusively from the trailing
    tercile_lookback values up to the PREVIOUS bar. Bar t never contributes to
    its own boundaries, so labels are point-in-time and never change when
    future bars are appended.
    """
    out = normalize_ohlcv(df)
    close = out["close"].astype(float)
    table = pd.DataFrame(index=out.index)
    table["close"] = close
    table["sma"] = close.rolling(window=sma_window, min_periods=sma_window).mean()
    table["trend_regime"] = np.where(
        table["sma"].isna(),
        INSUFFICIENT_HISTORY,
        np.where(close >= table["sma"], TREND_BULL, TREND_BEAR),
    )
    log_returns = np.log(close / close.shift(1))
    realized = log_returns.rolling(window=vol_window, min_periods=vol_window).std(ddof=1)
    table["realized_vol"] = realized * math.sqrt(TRADING_DAYS_PER_YEAR)
    history = table["realized_vol"].shift(1)
    lower = history.rolling(window=tercile_lookback, min_periods=tercile_lookback).quantile(1 / 3)
    upper = history.rolling(window=tercile_lookback, min_periods=tercile_lookback).quantile(2 / 3)
    table["vol_tercile_lower"] = lower
    table["vol_tercile_upper"] = upper
    conditions = [
        table["realized_vol"].isna() | lower.isna() | upper.isna(),
        table["realized_vol"] <= lower,
        table["realized_vol"] <= upper,
    ]
    choices = [INSUFFICIENT_HISTORY, VOL_TERCILE_LABELS[0], VOL_TERCILE_LABELS[1]]
    table["vol_regime"] = np.select(conditions, choices, default=VOL_TERCILE_LABELS[2])
    table["regime_key"] = table["trend_regime"] + "|" + table["vol_regime"]
    return table


def regime_at(
    df: pd.DataFrame,
    as_of: date | datetime | str | None = None,
    *,
    benchmark_symbol: str = "SPY",
    sma_window: int = 200,
    vol_window: int = 20,
    tercile_lookback: int = 252,
) -> dict[str, Any]:
    """Benchmark regime snapshot at the last bar on or before as_of."""
    if df is None or df.empty:
        return _empty_regime(benchmark_symbol)
    table = regime_table(
        df,
        sma_window=sma_window,
        vol_window=vol_window,
        tercile_lookback=tercile_lookback,
    )
    if as_of is not None:
        cutoff = pd.Timestamp(as_of)
        index = pd.DatetimeIndex(table.index)
        if index.tz is not None:
            cutoff = cutoff.tz_localize(index.tz) if cutoff.tzinfo is None else cutoff.tz_convert(index.tz)
        table = table[index <= cutoff]
    if table.empty:
        return _empty_regime(benchmark_symbol)
    row = table.iloc[-1]
    return {
        "benchmark_symbol": benchmark_symbol,
        "as_of_bar": pd.Timestamp(table.index[-1]).isoformat(),
        "trend_regime": str(row["trend_regime"]),
        "vol_regime": str(row["vol_regime"]),
        "regime_key": str(row["regime_key"]),
        "close": _round(row["close"]),
        "sma": _round(row["sma"]),
        "sma_window": int(sma_window),
        "realized_vol_annualized": _round(row["realized_vol"]),
        "vol_window": int(vol_window),
        "vol_tercile_lookback": int(tercile_lookback),
        "vol_tercile_lower": _round(row["vol_tercile_lower"]),
        "vol_tercile_upper": _round(row["vol_tercile_upper"]),
        "bars_available": int(len(table)),
        "source_bar_hash": _tail_hash(df),
        "point_in_time": True,
    }


def required_benchmark_bars(settings: Settings | None = None) -> int:
    """Bars of benchmark history needed for fully-labeled trend and terciles."""
    settings = settings or get_settings()
    return max(
        int(settings.market_regime_sma_window) + 10,
        int(settings.market_regime_vol_tercile_lookback)
        + int(settings.market_regime_vol_window)
        + 10,
    )


@dataclass(slots=True)
class MarketRegimeService:
    """Fetch the benchmark via the (cached) provider and label its regime."""

    provider: MarketDataProvider
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def current_regime(self) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        bars = required_benchmark_bars(settings)
        months = max(3, math.ceil(bars * 7 / 5 / 30) + 1)
        try:
            df = self.provider.fetch_ohlcv(
                settings.market_regime_benchmark_symbol,
                period=f"{months}mo",
                interval="1d",
            )
        except Exception:  # noqa: BLE001
            return _empty_regime(settings.market_regime_benchmark_symbol)
        return regime_at(
            df,
            benchmark_symbol=settings.market_regime_benchmark_symbol,
            sma_window=settings.market_regime_sma_window,
            vol_window=settings.market_regime_vol_window,
            tercile_lookback=settings.market_regime_vol_tercile_lookback,
        )


def _empty_regime(benchmark_symbol: str) -> dict[str, Any]:
    return {
        "benchmark_symbol": benchmark_symbol,
        "as_of_bar": None,
        "trend_regime": INSUFFICIENT_HISTORY,
        "vol_regime": INSUFFICIENT_HISTORY,
        "regime_key": f"{INSUFFICIENT_HISTORY}|{INSUFFICIENT_HISTORY}",
        "close": None,
        "sma": None,
        "realized_vol_annualized": None,
        "bars_available": 0,
        "source_bar_hash": "",
        "point_in_time": True,
    }


def _round(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return round(number, 8)


def _tail_hash(df: pd.DataFrame) -> str:
    cols = [col for col in ("open", "high", "low", "close", "volume") if col in df.columns]
    payload = df.tail(3)[cols].round(8).to_csv(index=True)
    return blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()
