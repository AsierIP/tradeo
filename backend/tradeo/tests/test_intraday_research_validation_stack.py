from __future__ import annotations

import pandas as pd
import pytest

from tradeo.modules.intraday.research import IntradayResearchConfig, IntradayResearchEvent
from tradeo.modules.intraday.research_validation_stack import (
    IntradayMatchedBaselineFactory,
    IntradayValidationStack,
    IntradayValidationThresholds,
)


def _target_bars() -> pd.DataFrame:
    idx = pd.date_range("2026-06-22 13:30", periods=6, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [10.0, 10.0, 10.0, 10.2, 10.4, 10.5],
            "high": [10.1, 10.5, 12.1, 12.2, 10.6, 10.7],
            "low": [9.9, 9.8, 9.9, 10.0, 10.2, 10.4],
            "close": [10.0, 10.2, 12.0, 12.1, 10.5, 10.6],
            "volume": [100_000, 120_000, 150_000, 180_000, 90_000, 80_000],
        },
        index=idx,
    )


def _slow_bars() -> pd.DataFrame:
    idx = pd.date_range("2026-06-22 13:30", periods=6, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [10.0, 10.0, 10.1, 10.2, 10.2, 10.2],
            "high": [10.1, 10.2, 10.3, 10.4, 10.3, 10.3],
            "low": [9.9, 9.95, 10.0, 10.1, 10.1, 10.1],
            "close": [10.0, 10.1, 10.2, 10.2, 10.2, 10.2],
            "volume": [100_000, 120_000, 150_000, 180_000, 90_000, 80_000],
        },
        index=idx,
    )


def _event(symbol: str, session_id: str, *, bucket: str, base_cost_r: float = 0.1) -> IntradayResearchEvent:
    return IntradayResearchEvent(
        symbol=symbol,
        session_id=session_id,
        signal_index=0,
        side="long",
        stop_price=9.0,
        target_price=12.0,
        max_bars=3,
        timeframe="5m",
        bucket=bucket,
        base_cost_r=base_cost_r,
        available_data_cutoff_index=0,
    )


def test_intraday_matched_baseline_factory_preserves_real_bucket_mix() -> None:
    bucket_a = "open|high_liquidity|rvol_high|gap_up|trend_up"
    bucket_b = "midday|medium_liquidity|rvol_mid|gap_flat|trend_flat"
    real = [
        _event("SOUN", "2026-06-22", bucket=bucket_a),
        _event("PLTR", "2026-06-22", bucket=bucket_a),
        _event("IONQ", "2026-06-22", bucket=bucket_b),
    ]
    pool = [
        _event("BASE1", "2026-06-22", bucket=bucket_a),
        _event("BASE2", "2026-06-22", bucket=bucket_b),
    ]

    matched = IntradayMatchedBaselineFactory().build(real, pool)

    assert matched.complete is True
    assert matched.bucket_counts == {bucket_a: 2, bucket_b: 1}
    assert [event.bucket_key for event in matched.events].count(bucket_a) == 2


def test_intraday_validation_stack_accepts_diverse_net_edge() -> None:
    bucket_a = "open|high_liquidity|rvol_high|gap_up|trend_up"
    bucket_b = "power_hour|high_liquidity|rvol_high|gap_up|trend_up"
    real = [
        _event("SOUN", "2026-06-22", bucket=bucket_a),
        _event("PLTR", "2026-06-23", bucket=bucket_b),
    ]
    baseline = [
        _event("BASE1", "2026-06-22", bucket=bucket_a),
        _event("BASE2", "2026-06-23", bucket=bucket_b),
    ]
    bars = {
        ("SOUN", "2026-06-22"): _target_bars(),
        ("PLTR", "2026-06-23"): _target_bars(),
        ("BASE1", "2026-06-22"): _slow_bars(),
        ("BASE2", "2026-06-23"): _slow_bars(),
    }

    report, validation = IntradayValidationStack(
        IntradayValidationThresholds(
            min_raw_events=2,
            min_effective_events=2.0,
            min_unique_symbols=2,
            min_unique_sessions=2,
            min_buckets=2,
            min_net_expectancy_r=0.05,
            min_edge_vs_baseline_r=0.01,
            min_profit_factor=1.1,
            max_symbol_concentration=0.60,
            max_session_concentration=0.60,
        )
    ).evaluate(real, bars, baseline_events=baseline)

    assert report.accepted is True
    assert validation.accepted is True
    assert validation.reason_codes == ()
    assert validation.metrics["effective_events"] == pytest.approx(2.0)
    assert validation.metrics["unique_buckets"] == 2


def test_intraday_validation_stack_rejects_concentration_even_when_report_passes() -> None:
    bucket = "open|high_liquidity|rvol_high|gap_up|trend_up"
    real = [
        _event("SOUN", "2026-06-22", bucket=bucket),
        _event("SOUN", "2026-06-23", bucket=bucket),
    ]
    baseline = [
        _event("BASE1", "2026-06-22", bucket=bucket),
        _event("BASE2", "2026-06-23", bucket=bucket),
    ]
    bars = {
        ("SOUN", "2026-06-22"): _target_bars(),
        ("SOUN", "2026-06-23"): _target_bars(),
        ("BASE1", "2026-06-22"): _slow_bars(),
        ("BASE2", "2026-06-23"): _slow_bars(),
    }

    report, validation = IntradayValidationStack(
        IntradayValidationThresholds(
            min_raw_events=2,
            min_effective_events=2.0,
            min_unique_symbols=2,
            min_unique_sessions=2,
            min_buckets=1,
            min_net_expectancy_r=0.05,
            min_edge_vs_baseline_r=0.01,
            min_profit_factor=1.1,
            max_symbol_concentration=0.60,
            max_session_concentration=0.60,
        )
    ).evaluate(
        real,
        bars,
        baseline_events=baseline,
        research_config=IntradayResearchConfig(require_all_cost_stress_positive=False),
    )

    assert report.accepted is True
    assert validation.accepted is False
    assert "insufficient_intraday_symbols" in validation.reason_codes
    assert "symbol_concentration_too_high" in validation.reason_codes
