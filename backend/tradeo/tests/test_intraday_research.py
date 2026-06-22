from __future__ import annotations

import pytest
import pandas as pd

from tradeo.modules.intraday.research import (
    IntradayResearchConfig,
    IntradayResearchEvent,
    evaluate_intraday_research,
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


def _event(
    symbol: str,
    session_id: str,
    *,
    signal_index: int = 0,
    bucket: str = "open|high_liquidity|rvol_high|gap_up|trend_up",
    base_cost_r: float = 0.1,
    max_bars: int = 3,
    available_data_cutoff_index: int | None = 0,
) -> IntradayResearchEvent:
    return IntradayResearchEvent(
        symbol=symbol,
        session_id=session_id,
        signal_index=signal_index,
        side="long",
        stop_price=9.0,
        target_price=12.0,
        max_bars=max_bars,
        timeframe="5m",
        bucket=bucket,
        base_cost_r=base_cost_r,
        available_data_cutoff_index=available_data_cutoff_index,
    )


def test_intraday_research_uses_canonical_triple_barrier_and_time_stop() -> None:
    real = [_event("SOUN", "2026-06-22", max_bars=3)]
    null = [_event("NULL", "2026-06-22", max_bars=3)]
    report = evaluate_intraday_research(
        real,
        {
            ("SOUN", "2026-06-22"): _slow_bars(),
            ("NULL", "2026-06-22"): _slow_bars(),
        },
        null_events=null,
        config=IntradayResearchConfig(require_all_cost_stress_positive=False),
    )

    outcome = report.evidence_outcomes[0]

    assert outcome.reason == "time"
    assert report.label_counts == {"time_stop": 1}
    assert outcome.gross_r == pytest.approx(0.2)
    assert outcome.net_r_by_cost[1.0] == pytest.approx(0.1)


def test_intraday_research_stratifies_null_deoverlaps_and_cost_stresses() -> None:
    bucket = "open|high_liquidity|rvol_high|gap_up|trend_up"
    real = [
        _event("SOUN", "2026-06-22", signal_index=0, bucket=bucket),
        _event("SOUN", "2026-06-22", signal_index=1, bucket=bucket),
        _event("PLTR", "2026-06-22", signal_index=0, bucket=bucket),
    ]
    null = [
        _event("NULL1", "2026-06-22", bucket=bucket),
        _event("NULL2", "2026-06-22", bucket=bucket),
    ]
    report = evaluate_intraday_research(
        real,
        {
            ("SOUN", "2026-06-22"): _target_bars(),
            ("PLTR", "2026-06-22"): _target_bars(),
            ("NULL1", "2026-06-22"): _slow_bars(),
            ("NULL2", "2026-06-22"): _slow_bars(),
        },
        null_events=null,
    )

    assert report.accepted is True
    assert report.reason_codes == ()
    assert report.deoverlap["eligible_before_deoverlap"] == 3
    assert report.deoverlap["kept"] == 2
    assert report.deoverlap["dropped_symbol_session_overlap"] == 1
    assert report.gross_expectancy_r == pytest.approx(2.0)
    assert report.cost_stress[1.0].expectancy_r == pytest.approx(1.9)
    assert report.cost_stress[2.0].expectancy_r == pytest.approx(1.8)
    assert report.cost_stress[3.0].expectancy_r == pytest.approx(1.7)
    assert report.cost_stress[3.0].edge_vs_null_r == pytest.approx(1.8)
    assert report.null_baseline[1.0]["method"] == "stratified_by_intraday_bucket_v1"
    assert report.bucket_counts == {bucket: 2}


def test_intraday_research_rejects_gross_ev_only() -> None:
    bucket = "midday|medium_liquidity|rvol_mid|gap_flat|trend_flat"
    real = [_event("SOUN", "2026-06-22", bucket=bucket, base_cost_r=0.3)]
    null = [_event("NULL", "2026-06-22", bucket=bucket, base_cost_r=0.3)]
    report = evaluate_intraday_research(
        real,
        {
            ("SOUN", "2026-06-22"): _slow_bars(),
            ("NULL", "2026-06-22"): _slow_bars(),
        },
        null_events=null,
    )

    assert report.gross_expectancy_r == pytest.approx(0.2)
    assert report.net_expectancy_r == pytest.approx(-0.1)
    assert report.accepted is False
    assert "gross_ev_only" in report.reason_codes
    assert "net_ev_below_threshold_1x" in report.reason_codes


def test_intraday_research_rejects_lookahead_cutoff() -> None:
    bucket = "open|high_liquidity|rvol_high|gap_up|trend_up"
    real = [_event("SOUN", "2026-06-22", bucket=bucket, available_data_cutoff_index=1)]
    null = [_event("NULL", "2026-06-22", bucket=bucket)]
    report = evaluate_intraday_research(
        real,
        {
            ("SOUN", "2026-06-22"): _target_bars(),
            ("NULL", "2026-06-22"): _slow_bars(),
        },
        null_events=null,
    )

    assert report.accepted is False
    assert "lookahead_detected" in report.reason_codes
    assert report.evidence_outcomes == ()
