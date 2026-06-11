from __future__ import annotations

import numpy as np
import pandas as pd

from tradeo.core.config import Settings
from tradeo.services.market_regime import (
    INSUFFICIENT_HISTORY,
    TREND_BEAR,
    TREND_BULL,
    MarketRegimeService,
    regime_at,
    regime_table,
    required_benchmark_bars,
)


def _frame(closes: list[float], *, start: str = "2024-01-02") -> pd.DataFrame:
    idx = pd.bdate_range(start, periods=len(closes))
    closes_arr = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": closes_arr,
            "high": closes_arr * 1.01,
            "low": closes_arr * 0.99,
            "close": closes_arr,
            "volume": np.full(len(closes_arr), 1_000_000.0),
        },
        index=idx,
    )


def _alternating(base: float, amplitude: float, bars: int) -> list[float]:
    return [base + (amplitude if i % 2 else -amplitude) for i in range(bars)]


def test_trend_regime_bull_and_bear() -> None:
    rising = _frame([100.0 + 0.5 * i for i in range(260)])
    falling = _frame([300.0 - 0.5 * i for i in range(260)])

    bull = regime_at(rising, sma_window=200, vol_window=20, tercile_lookback=30)
    bear = regime_at(falling, sma_window=200, vol_window=20, tercile_lookback=30)

    assert bull["trend_regime"] == TREND_BULL
    assert bear["trend_regime"] == TREND_BEAR
    assert bull["close"] > bull["sma"]
    assert bear["close"] < bear["sma"]


def test_trend_requires_full_sma_window() -> None:
    short = _frame([100.0 + i for i in range(150)])

    snapshot = regime_at(short, sma_window=200, vol_window=20, tercile_lookback=30)

    assert snapshot["trend_regime"] == INSUFFICIENT_HISTORY
    assert snapshot["sma"] is None


def test_vol_tercile_high_after_calm_history() -> None:
    closes = _alternating(100.0, 0.05, 320) + _alternating(100.0, 3.0, 40)
    snapshot = regime_at(_frame(closes), sma_window=50, vol_window=20, tercile_lookback=252)

    assert snapshot["vol_regime"] == "high_vol_tercile"
    assert snapshot["realized_vol_annualized"] > snapshot["vol_tercile_upper"]


def test_vol_tercile_low_after_turbulent_history() -> None:
    closes = _alternating(100.0, 3.0, 320) + _alternating(100.0, 0.05, 40)
    snapshot = regime_at(_frame(closes), sma_window=50, vol_window=20, tercile_lookback=252)

    assert snapshot["vol_regime"] == "low_vol_tercile"


def test_regime_labels_are_point_in_time_stable() -> None:
    closes = [100.0 + np.sin(i / 7.0) * 4.0 + 0.2 * i for i in range(360)]
    full = _frame(closes)
    truncated = full.iloc[:330]

    full_table = regime_table(full, sma_window=100, vol_window=20, tercile_lookback=120)
    truncated_table = regime_table(truncated, sma_window=100, vol_window=20, tercile_lookback=120)

    overlap = truncated_table.index
    pd.testing.assert_series_equal(
        full_table.loc[overlap, "vol_regime"], truncated_table["vol_regime"]
    )
    pd.testing.assert_series_equal(
        full_table.loc[overlap, "trend_regime"], truncated_table["trend_regime"]
    )
    pd.testing.assert_series_equal(
        full_table.loc[overlap, "regime_key"], truncated_table["regime_key"]
    )


def test_regime_at_respects_as_of_cutoff() -> None:
    df = _frame([100.0 + 0.5 * i for i in range(280)])
    cutoff = df.index[219]

    snapshot = regime_at(df, as_of=cutoff, sma_window=200, vol_window=20, tercile_lookback=30)

    assert snapshot["as_of_bar"] == pd.Timestamp(cutoff).isoformat()
    assert snapshot["bars_available"] == 220


def test_regime_at_empty_frame_is_honest() -> None:
    snapshot = regime_at(pd.DataFrame())

    assert snapshot["trend_regime"] == INSUFFICIENT_HISTORY
    assert snapshot["vol_regime"] == INSUFFICIENT_HISTORY
    assert snapshot["bars_available"] == 0


def test_regime_key_combines_trend_and_vol() -> None:
    closes = _alternating(100.0, 0.05, 320) + _alternating(120.0, 3.0, 40)
    df = _frame(closes)
    df["close"] = df["close"].to_numpy() + np.linspace(0.0, 60.0, len(df))
    df["open"] = df["close"]
    df["high"] = df["close"] * 1.01
    df["low"] = df["close"] * 0.99

    snapshot = regime_at(df, sma_window=200, vol_window=20, tercile_lookback=120)

    assert snapshot["regime_key"] == f"{snapshot['trend_regime']}|{snapshot['vol_regime']}"
    assert snapshot["point_in_time"] is True
    assert snapshot["source_bar_hash"]


def test_market_regime_service_uses_provider_and_settings() -> None:
    settings = Settings(
        market_regime_benchmark_symbol="SPY",
        market_regime_sma_window=50,
        market_regime_vol_window=10,
        market_regime_vol_tercile_lookback=60,
    )

    class Provider:
        calls: list[tuple[str, str, str]] = []

        def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
            type(self).calls.append((symbol, period, interval))
            return _frame([100.0 + 0.3 * i for i in range(200)])

    snapshot = MarketRegimeService(provider=Provider(), settings=settings).current_regime()

    assert Provider.calls and Provider.calls[0][0] == "SPY"
    assert Provider.calls[0][2] == "1d"
    assert snapshot["benchmark_symbol"] == "SPY"
    assert snapshot["trend_regime"] == TREND_BULL
    assert snapshot["vol_regime"] in {"low_vol_tercile", "mid_vol_tercile", "high_vol_tercile"}


def test_market_regime_service_survives_provider_failure() -> None:
    class Broken:
        def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
            raise ConnectionError("gateway down")

    snapshot = MarketRegimeService(provider=Broken(), settings=Settings()).current_regime()

    assert snapshot["trend_regime"] == INSUFFICIENT_HISTORY
    assert snapshot["bars_available"] == 0


def test_required_benchmark_bars_covers_sma_and_terciles() -> None:
    settings = Settings(
        market_regime_sma_window=200,
        market_regime_vol_window=20,
        market_regime_vol_tercile_lookback=252,
    )

    assert required_benchmark_bars(settings) >= 282
