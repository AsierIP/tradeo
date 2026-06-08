from __future__ import annotations

import numpy as np
import pandas as pd


def fixture_ohlcv(symbol: str, bars: int = 420) -> pd.DataFrame:
    seed = abs(hash(symbol)) % (2**32)
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.025, bars)
    price = 20 * np.exp(np.cumsum(returns))
    if seed % 3 == 0 and bars > 150:
        n = 100
        x = np.linspace(-1, 1, n)
        cup = 1 - 0.22 * (1 - x**2)
        base = price[-n] * cup * (1 + np.linspace(0, 0.08, n))
        price[-n:] = base * (1 + rng.normal(0, 0.012, n))
        price[-1] = max(price[-20:]) * 1.015
    open_ = price * (1 + rng.normal(0, 0.008, bars))
    high = np.maximum(open_, price) * (1 + rng.uniform(0.005, 0.025, bars))
    low = np.minimum(open_, price) * (1 - rng.uniform(0.005, 0.025, bars))
    volume = rng.integers(300_000, 3_000_000, bars).astype(float)
    if seed % 3 == 0:
        volume[-1] *= 2.5
    idx = pd.date_range(end=pd.Timestamp.utcnow().date(), periods=bars, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": price, "volume": volume}, index=idx
    )
