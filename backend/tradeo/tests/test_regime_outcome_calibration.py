from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from tradeo.core.config import Settings
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.types import ForwardOutcome, WindowSample
from tradeo.services.market_regime import (
    MarketRegimeService,
    period_to_months,
    regime_keys_for_dates,
    unlabeled_regime_key,
)

BULL_LOW = "benchmark_bull|low_vol_tercile"
BEAR_HIGH = "benchmark_bear|high_vol_tercile"


def _regime_table(keys_by_date: dict[str, str]) -> pd.DataFrame:
    index = pd.DatetimeIndex(sorted(keys_by_date))
    table = pd.DataFrame(
        {"regime_key": [keys_by_date[str(ts.date())] for ts in index]},
        index=index,
    )
    table.attrs["benchmark_symbol"] = "SPY"
    return table


def _sample(end: str, *, win: bool) -> WindowSample:
    entry = 100.0
    risk = 10.0
    if win:
        # Long target at entry + rr*risk is touched before the stop.
        opens, highs, lows, closes = [101.0], [125.0], [96.0], [120.0]
    else:
        opens, highs, lows, closes = [99.0], [101.0], [85.0], [88.0]
    return WindowSample(
        symbol="REGT",
        timeframe="1d",
        window_size=20,
        start="2024-01-01",
        end=end,
        year=int(end[:4]),
        vector=np.asarray([1.0, 0.5], dtype=np.float32),
        chart={},
        features={},
        outcome=ForwardOutcome(
            forward_returns={5: closes[-1] / entry - 1.0},
            entry_price=entry,
            risk_proxy=risk,
            forward_end=end,
            long_mfe_r=(max(highs) - entry) / risk,
            long_mae_r=max(0.0, (entry - min(lows)) / risk),
            long_outcome_r=(closes[-1] - entry) / risk,
            long_hit_4r=False,
            short_mfe_r=(entry - min(lows)) / risk,
            short_mae_r=max(0.0, (max(highs) - entry) / risk),
            short_outcome_r=(entry - closes[-1]) / risk,
            short_hit_4r=False,
            forward_opens=opens,
            forward_highs=highs,
            forward_lows=lows,
            forward_closes=closes,
        ),
    )


def test_regime_keys_for_dates_is_point_in_time() -> None:
    table = _regime_table(
        {
            "2024-03-01": BULL_LOW,
            "2024-03-04": BEAR_HIGH,
        }
    )

    keys = regime_keys_for_dates(
        table,
        ["2024-02-28", "2024-03-01", "2024-03-03", "2024-03-04", "2024-03-10"],
    )

    assert keys == [unlabeled_regime_key(), BULL_LOW, BULL_LOW, BEAR_HIGH, BEAR_HIGH]


def test_regime_keys_for_dates_without_table_is_unlabeled() -> None:
    assert regime_keys_for_dates(None, ["2024-03-01"]) == [unlabeled_regime_key()]
    empty = pd.DataFrame({"regime_key": []}, index=pd.DatetimeIndex([]))
    assert regime_keys_for_dates(empty, ["2024-03-01"]) == [unlabeled_regime_key()]


def test_period_to_months_parses_provider_periods() -> None:
    assert period_to_months("2y") == 24
    assert period_to_months("6mo") == 6
    assert period_to_months("90d") == 3
    assert period_to_months("max") == 120
    assert period_to_months(None) == 0
    assert period_to_months("not-a-period") == 0


def test_history_table_covers_period_plus_warmup_and_records_config() -> None:
    requested: dict[str, str] = {}

    class Provider:
        def fetch_ohlcv(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame:
            requested.update({"symbol": symbol, "period": period, "interval": interval})
            closes = np.asarray([100.0 + 0.1 * i for i in range(400)])
            idx = pd.bdate_range("2023-01-02", periods=len(closes))
            return pd.DataFrame(
                {
                    "open": closes,
                    "high": closes * 1.01,
                    "low": closes * 0.99,
                    "close": closes,
                    "volume": np.full(len(closes), 1_000_000.0),
                },
                index=idx,
            )

    settings = Settings(
        market_regime_benchmark_symbol="SPY",
        market_regime_sma_window=50,
        market_regime_vol_window=10,
        market_regime_vol_tercile_lookback=60,
    )

    table = MarketRegimeService(provider=Provider(), settings=settings).history_table(period="1y")

    assert requested["symbol"] == "SPY"
    assert requested["interval"] == "1d"
    requested_months = int(requested["period"].removesuffix("mo"))
    assert requested_months >= 12 + 3
    assert "regime_key" in table.columns
    assert table.attrs["benchmark_symbol"] == "SPY"
    assert table.attrs["sma_window"] == 50
    assert set(regime_keys_for_dates(table, [table.index[-1]])) != {unlabeled_regime_key()}


def test_benchmark_regime_outcomes_buckets_by_pit_regime() -> None:
    table = _regime_table(
        {
            "2024-03-01": BULL_LOW,
            "2024-06-03": BEAR_HIGH,
        }
    )
    engine = ClusterResearchEngine(benchmark_regime_table=table)
    samples = [
        _sample("2024-03-05", win=True),
        _sample("2024-03-06", win=True),
        _sample("2024-06-10", win=False),
        _sample("2024-02-01", win=True),  # before benchmark history -> unlabeled
    ]

    outcomes = engine._benchmark_regime_outcomes(samples, side="long", rr=2.0)

    assert outcomes["available"] is True
    assert outcomes["benchmark_symbol"] == "SPY"
    assert outcomes["labeled_sample_count"] == 3
    assert outcomes["unlabeled_sample_count"] == 1
    buckets = outcomes["buckets"]
    # Canonical simulation enters at the next bar's open, so R is path-derived;
    # the sign and win rate per bucket are the contract here.
    assert buckets[BULL_LOW]["sample_count"] == 2
    assert buckets[BULL_LOW]["expectancy_r"] > 0.0
    assert buckets[BULL_LOW]["win_rate"] == 1.0
    assert buckets[BEAR_HIGH]["sample_count"] == 1
    assert buckets[BEAR_HIGH]["expectancy_r"] < 0.0
    assert buckets[BEAR_HIGH]["win_rate"] == 0.0
    assert unlabeled_regime_key() in buckets


def test_benchmark_regime_outcomes_unavailable_without_table() -> None:
    engine = ClusterResearchEngine()

    outcomes = engine._benchmark_regime_outcomes([_sample("2024-03-05", win=True)], side="long", rr=2.0)

    assert outcomes["available"] is False
    assert outcomes["buckets"] == {}


def _pattern(benchmark_regime_outcomes: dict | None) -> SimpleNamespace:
    profile: dict = {
        "preferred_regime_keys": ["calm|bull|risk_on"],
        "bucket_counts": {"calm|bull|risk_on": 10},
    }
    if benchmark_regime_outcomes is not None:
        profile["benchmark_regime_outcomes"] = benchmark_regime_outcomes
    return SimpleNamespace(metrics_json={"regime_profile": profile})


def _regime(regime_key: str) -> dict:
    return {
        "regime_key": "calm|bull|risk_on",
        "benchmark_regime": {"regime_key": regime_key},
    }


def _outcomes(bucket: dict) -> dict:
    return {
        "available": True,
        "method": "pit_benchmark_regime_at_sample_end+canonical_triple_barrier",
        "side": "long",
        "rr": 2.5,
        "benchmark_symbol": "SPY",
        "buckets": {BULL_LOW: bucket},
    }


def test_pattern_regime_fit_calibrated_positive_bucket() -> None:
    settings = Settings(market_regime_outcome_min_samples=3)
    pattern = _pattern(_outcomes({"sample_count": 8, "expectancy_r": 0.4, "win_rate": 0.5, "profit_factor": 1.8}))

    fit = NovelPatternMatcher._pattern_regime_fit(pattern, _regime(BULL_LOW), settings)

    assert fit["label"] == "calibrated_regime_positive"
    assert fit["matched"] is True
    assert fit["hard_gate_blocked"] is False
    assert fit["score"] == 0.85
    assert fit["calibration"]["sample_count"] == 8
    assert fit["calibration"]["regime_key"] == BULL_LOW


def test_pattern_regime_fit_calibrated_negative_bucket_is_hard_gate_eligible() -> None:
    settings = Settings(market_regime_outcome_min_samples=3)
    pattern = _pattern(_outcomes({"sample_count": 9, "expectancy_r": -0.3, "win_rate": 0.2, "profit_factor": 0.4}))

    fit = NovelPatternMatcher._pattern_regime_fit(pattern, _regime(BULL_LOW), settings)

    assert fit["label"] == "calibrated_regime_negative"
    assert fit["matched"] is False
    assert fit["hard_gate_blocked"] is True
    assert fit["score"] == 0.2


def test_pattern_regime_fit_falls_back_when_bucket_too_small() -> None:
    settings = Settings(market_regime_outcome_min_samples=12)
    pattern = _pattern(_outcomes({"sample_count": 5, "expectancy_r": -0.3, "win_rate": 0.2, "profit_factor": 0.4}))

    fit = NovelPatternMatcher._pattern_regime_fit(pattern, _regime(BULL_LOW), settings)

    # Falls back to the preferred-regime heuristic on the local regime key.
    assert fit["label"] == "preferred_regime"
    assert "hard_gate_blocked" not in fit


def test_pattern_regime_fit_falls_back_for_unlabeled_benchmark_regime() -> None:
    settings = Settings(market_regime_outcome_min_samples=3)
    pattern = _pattern(_outcomes({"sample_count": 9, "expectancy_r": -0.3, "win_rate": 0.2, "profit_factor": 0.4}))

    fit = NovelPatternMatcher._pattern_regime_fit(pattern, _regime(unlabeled_regime_key()), settings)

    assert fit["label"] == "preferred_regime"


def test_pattern_regime_fit_without_settings_keeps_legacy_behavior() -> None:
    pattern = _pattern(_outcomes({"sample_count": 9, "expectancy_r": -0.3, "win_rate": 0.2, "profit_factor": 0.4}))

    fit = NovelPatternMatcher._pattern_regime_fit(pattern, _regime(BULL_LOW))

    assert fit["label"] == "preferred_regime"
