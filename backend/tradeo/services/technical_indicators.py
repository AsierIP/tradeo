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
    """Normalize provider-specific OHLCV columns and enforce sane market bars."""
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
    out = out.sort_index()
    validate_ohlcv(out)
    return out


def validate_ohlcv(df: pd.DataFrame, *, require_timezone: bool = False) -> None:
    """Raise on OHLCV data errors that can silently create false patterns.

    The validator intentionally focuses on invariants that must hold for every
    provider before research sampling, clustering or matching. Timezone remains
    optional here because some historical daily feeds are date-indexed, but audit
    packages must still document timezone separately.
    """
    if df.empty:
        return
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"OHLCV data missing required columns: {missing}")
    if df.index.has_duplicates:
        raise ValueError("OHLCV index contains duplicate timestamps")
    if not df.index.is_monotonic_increasing:
        raise ValueError("OHLCV index must be sorted ascending before validation")
    if require_timezone and isinstance(df.index, pd.DatetimeIndex) and df.index.tz is None:
        raise ValueError("OHLCV DatetimeIndex must include timezone")

    values = df[required]
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("OHLCV data contains non-finite values")
    if (values[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be strictly positive")
    if (values["volume"] < 0).any():
        raise ValueError("OHLCV volume must be non-negative")
    if (values["high"] < values["low"]).any():
        raise ValueError("OHLC high must be greater than or equal to low")
    if (values["high"] < values[["open", "close"]].max(axis=1)).any():
        raise ValueError("OHLC high must be greater than or equal to open and close")
    if (values["low"] > values[["open", "close"]].min(axis=1)).any():
        raise ValueError("OHLC low must be less than or equal to open and close")


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
