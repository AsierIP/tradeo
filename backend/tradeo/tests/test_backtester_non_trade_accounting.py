from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from tradeo.schemas import PatternCandidate
from tradeo.services.backtester import Backtester


@dataclass
class _Params:
    max_holding_bars: int = 5


class _StubDetector:
    """Fires exactly one candidate at the first eligible bar (i=230)."""

    def __init__(self) -> None:
        self.params = _Params()

    def detect(self, symbol: str, lookback: pd.DataFrame) -> PatternCandidate | None:
        if len(lookback) != 231:
            return None
        return PatternCandidate(
            symbol=symbol,
            entry=100.0,
            stop=95.0,
            target=110.0,
            reward_risk=2.0,
            confidence=0.8,
            rule_score=0.8,
            ml_score=0.8,
            vision_score=0.8,
            composite_score=0.8,
        )


class _StubProvider:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def fetch_ohlcv(self, symbol: str, period: str = "3y", interval: str = "1d") -> pd.DataFrame:
        return self._df


def _flat_df(n: int = 300) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=n, freq="B")
    base = np.full(n, 100.0)
    return pd.DataFrame(
        {"open": base, "high": base + 1.0, "low": base - 1.0, "close": base},
        index=index,
    )


def test_gap_prefiltered_signal_counts_as_skipped_not_trade() -> None:
    df = _flat_df()
    df.iloc[231, df.columns.get_loc("open")] = 120.0  # >8% above candidate entry
    metrics = Backtester(provider=_StubProvider(df), detector=_StubDetector()).run(["TST"])
    assert metrics.total_signals == 1
    assert metrics.skipped_signals == 1
    assert metrics.total_trades == 0
    assert metrics.skip_rate == 1.0
    assert metrics.expectancy_r == 0.0


def test_executed_signal_counts_as_trade_with_zero_skips() -> None:
    df = _flat_df()
    df.iloc[233, df.columns.get_loc("high")] = 111.0  # target 110 hit two bars in
    metrics = Backtester(provider=_StubProvider(df), detector=_StubDetector()).run(["TST"])
    assert metrics.total_signals == 1
    assert metrics.skipped_signals == 0
    assert metrics.total_trades == 1
    assert metrics.skip_rate == 0.0
    assert metrics.trades[0]["outcome"].startswith("target")
