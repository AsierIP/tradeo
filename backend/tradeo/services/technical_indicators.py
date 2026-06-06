from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=max(2, window // 2)).mean()


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(window=window, min_periods=window).mean()


def max_drawdown_pct(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    curve = np.asarray(equity_curve, dtype=float)
    running_max = np.maximum.accumulate(curve)
    drawdowns = (curve - running_max) / np.where(running_max == 0, 1, running_max)
    return float(abs(drawdowns.min()) * 100)


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize provider-specific OHLCV columns to lower-case names."""
    if df.empty:
        return df
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(c[0]).lower() for c in out.columns]
    else:
        out.columns = [str(c).lower().replace(" ", "_") for c in out.columns]
    aliases = {"adj_close": "close", "volume": "volume"}
    for src, dst in aliases.items():
        if dst not in out.columns and src in out.columns:
            out[dst] = out[src]
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"OHLCV data missing required columns: {missing}")
    out = out[required].dropna()
    out = out.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    return out


def seeded_synthetic_ohlcv(symbol: str, bars: int = 420) -> pd.DataFrame:
    """Generate deterministic synthetic OHLCV for offline demos/tests.

    This is never used for trading decisions when live data is available. It keeps the
    dashboard and tests functional on machines without market data connectivity.
    """
    seed = abs(hash(symbol)) % (2**32)
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.025, bars)
    price = 20 * np.exp(np.cumsum(returns))
    # Inject an approximate cup in the last 120 bars for a subset of tickers.
    if seed % 3 == 0 and bars > 150:
        n = 100
        x = np.linspace(-1, 1, n)
        cup = 1 - 0.22 * (1 - x**2)
        base = price[-n] * cup * (1 + np.linspace(0, 0.08, n))
        price[-n:] = base * (1 + rng.normal(0, 0.012, n))
        price[-1] = max(price[-20:]) * 1.015
    high = price * (1 + rng.uniform(0.005, 0.025, bars))
    low = price * (1 - rng.uniform(0.005, 0.025, bars))
    open_ = price * (1 + rng.normal(0, 0.008, bars))
    volume = rng.integers(300_000, 3_000_000, bars).astype(float)
    if seed % 3 == 0:
        volume[-1] *= 2.5
    idx = pd.date_range(end=pd.Timestamp.utcnow().date(), periods=bars, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": price, "volume": volume}, index=idx
    )
