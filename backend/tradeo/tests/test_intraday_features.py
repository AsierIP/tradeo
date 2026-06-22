from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from tradeo.modules.intraday.features import (
    CONTRACT_VERSION,
    IntradayFeatureBuilder,
    IntradayFeatureConfig,
)


def _bars() -> pd.DataFrame:
    idx = pd.date_range("2026-06-22 13:30", periods=5, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [10.0, 10.2, 10.4, 10.8, 11.0],
            "high": [10.3, 10.5, 10.9, 11.1, 11.4],
            "low": [9.9, 10.1, 10.3, 10.7, 10.9],
            "close": [10.2, 10.4, 10.8, 11.0, 11.2],
            "volume": [100_000, 120_000, 150_000, 160_000, 180_000],
            "bid": [10.19, 10.39, 10.79, 10.99, 11.19],
            "ask": [10.21, 10.41, 10.81, 11.01, 11.21],
        },
        index=idx,
    )


def test_intraday_feature_builder_computes_core_contract_features() -> None:
    bars = _bars()
    baseline = {0: 50_000, 5: 60_000, 10: 75_000, 15: 80_000, 20: 90_000}
    builder = IntradayFeatureBuilder(
        IntradayFeatureConfig(
            opening_range_minutes=15,
            atr_window=3,
            medium_liquidity_dollar_volume=500_000,
            high_liquidity_dollar_volume=1_000_000,
            tight_spread_bps=25.0,
        )
    )

    result = builder.build(
        bars,
        symbol="soun",
        previous_close=9.5,
        minute_volume_baseline=baseline,
        timeframe="5m",
        session_open=pd.Timestamp("2026-06-22 13:30", tz="UTC"),
    )

    frame = result.frame
    first_typical = (10.3 + 9.9 + 10.2) / 3.0

    assert result.symbol == "SOUN"
    assert result.contract_version == CONTRACT_VERSION
    assert frame["contract_version"].nunique() == 1
    assert frame["contract_version"].iloc[0] == CONTRACT_VERSION
    assert math.isclose(float(frame["vwap"].iloc[0]), first_typical)
    assert math.isclose(
        float(frame["distance_to_vwap"].iloc[0]),
        10.2 / first_typical - 1.0,
        rel_tol=1e-12,
    )
    assert frame["opening_range_high"].tolist() == [10.9] * 5
    assert frame["opening_range_low"].tolist() == [9.9] * 5
    assert math.isclose(float(frame["gap_pct"].iloc[0]), (10.0 / 9.5 - 1.0) * 100.0)
    assert frame["rvol"].tolist() == [2.0, 2.0, 2.0, 2.0, 2.0]
    assert math.isclose(float(frame["dollar_volume"].iloc[-1]), 11.2 * 180_000)
    assert frame["session_bucket"].tolist() == ["open"] * 5
    assert frame["liquidity_bucket"].iloc[-1] == "high"
    assert set(result.feature_columns).issuperset(
        {"vwap", "distance_to_vwap", "rvol", "atr", "spread_proxy_bps", "dollar_volume"}
    )


def test_intraday_feature_builder_rejects_nan_inf_and_bad_rvol_baseline() -> None:
    builder = IntradayFeatureBuilder()
    bars = _bars()
    bad_bars = bars.copy()
    bad_bars.loc[bad_bars.index[1], "close"] = np.inf

    with pytest.raises(ValueError, match="non-finite"):
        builder.build(
            bad_bars,
            symbol="BAD",
            previous_close=9.5,
            minute_volume_baseline={0: 50_000, 5: 60_000, 10: 75_000, 15: 80_000, 20: 90_000},
            session_open=pd.Timestamp("2026-06-22 13:30", tz="UTC"),
        )

    with pytest.raises(ValueError, match="baseline"):
        builder.build(
            bars,
            symbol="BAD",
            previous_close=9.5,
            minute_volume_baseline={0: 50_000, 5: 0, 10: 75_000, 15: 80_000, 20: 90_000},
            session_open=pd.Timestamp("2026-06-22 13:30", tz="UTC"),
        )
