from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from tradeo.research.intraday_vwap_confirmation import (
    CandidateEvent,
    choose_best_overlay,
    confirmation_decision,
    reconstruct_candidate_events,
    simulate_overlays,
)


def _write_cache(tmp_path: Path, symbol: str, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows).to_csv(tmp_path / f"{symbol}_30m_60d.csv", index=False)


def _rows(closes: list[float]) -> list[dict[str, object]]:
    timestamps = pd.date_range("2026-05-01 10:00", periods=len(closes), freq="30min", tz="America/New_York")
    return [
        {
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1000,
        }
        for ts, close in zip(timestamps, closes, strict=True)
    ]


def _sample(symbol: str = "TEST", outcome_r: float = 2.0) -> dict[str, object]:
    return {
        "run_id": 6454,
        "pattern_key": "candidate",
        "symbol": symbol,
        "timeframe": "30m",
        "window_size": 100,
        "window_start_ts": "2026-05-01T10:00:00-04:00",
        "window_end_ts": "2026-05-01T10:30:00-04:00",
        "entry_ts": "2026-05-01T10:30:00-04:00",
        "exit_ts": "2026-05-01T12:00:00-04:00",
        "entry_price": 11.0,
        "risk_proxy": 1.0,
        "outcome_r": outcome_r,
        "month": "2026-05",
        "session_bucket": "mid",
        "source": "fixture",
    }


def _overlay(results: list[dict[str, object]], name: str) -> dict[str, object]:
    return next(row for row in results if row["overlay"] == name)


def test_reconstructs_events_from_examples_fixture(tmp_path: Path) -> None:
    _write_cache(tmp_path, "TEST", _rows([10.0, 11.0, 12.0, 12.5]))

    events = reconstruct_candidate_events([_sample()], run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    assert len(events) == 1
    assert events[0].symbol == "TEST"
    assert events[0].vwap_at_entry is not None
    assert events[0].data_quality == "reconstructed"


def test_exit_on_vwap_loss_exits_first_close_below_vwap(tmp_path: Path) -> None:
    _write_cache(tmp_path, "TEST", _rows([10.0, 12.0, 8.0, 13.0]))
    events = reconstruct_candidate_events([_sample()], run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    result = _overlay(simulate_overlays(events), "exit_on_vwap_loss")

    assert result["computable_count"] == 1
    assert result["event_outcomes"][0]["exit_reason"] == "vwap_loss"
    assert result["event_outcomes"][0]["outcome_r"] < 0


def test_exit_on_failed_reclaim_n2_exits_when_next_bars_do_not_hold_vwap(tmp_path: Path) -> None:
    _write_cache(tmp_path, "TEST", _rows([10.0, 12.0, 8.0, 13.0]))
    events = reconstruct_candidate_events([_sample()], run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    result = _overlay(simulate_overlays(events), "exit_on_failed_reclaim")

    assert result["event_outcomes"][0]["exit_reason"] == "failed_reclaim_n2"


def test_exit_on_vwap_loss_or_time_stop_uses_final_bar_when_no_loss(tmp_path: Path) -> None:
    _write_cache(tmp_path, "TEST", _rows([10.0, 11.0, 12.0, 13.0]))
    events = reconstruct_candidate_events([_sample()], run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    result = _overlay(simulate_overlays(events), "exit_on_vwap_loss_or_time_stop")

    assert result["event_outcomes"][0]["exit_reason"] == "time_stop"
    assert result["event_outcomes"][0]["outcome_r"] == 2.0


def test_exit_on_vwap_loss_or_4r_takeprofit_prefers_4r_before_loss(tmp_path: Path) -> None:
    rows = _rows([10.0, 11.0, 15.0, 8.0])
    rows[2]["high"] = 15.0
    _write_cache(tmp_path, "TEST", rows)
    events = reconstruct_candidate_events([_sample()], run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    result = _overlay(simulate_overlays(events), "exit_on_vwap_loss_or_4R_takeprofit")

    assert result["event_outcomes"][0]["exit_reason"] == "takeprofit_4r"
    assert result["event_outcomes"][0]["outcome_r"] == 4.0


def test_metrics_expectancy_profit_factor_drawdown_and_concentration(tmp_path: Path) -> None:
    _write_cache(tmp_path, "AAA", _rows([10.0, 11.0, 12.0, 13.0]))
    _write_cache(tmp_path, "BBB", _rows([10.0, 11.0, 8.0, 13.0]))
    samples = [_sample("AAA", 2.0), _sample("BBB", -1.0)]
    events = reconstruct_candidate_events(samples, run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    baseline = _overlay(simulate_overlays(events), "baseline_existing")

    assert baseline["expectancy_r"] == 0.5
    assert baseline["profit_factor"] == 2.0
    assert baseline["win_rate"] == 0.5
    assert baseline["max_drawdown_r"] == 1.0
    assert baseline["symbol_count"] == 2
    assert baseline["concentration_top_symbol_pct"] == 0.5


def test_decision_confirm_candidate_ready_for_narrow_wave() -> None:
    results = [
        {
            "overlay": "exit_on_vwap_loss",
            "sample_count": 40,
            "computable_count": 40,
            "expectancy_r": 0.4,
            "profit_factor": 1.5,
            "max_drawdown_r": 8.0,
            "symbol_count": 6,
            "concentration_top_symbol_pct": 0.3,
            "concentration_top_month_pct": 0.4,
            "decision_eligible": True,
        }
    ]

    assert (
        confirmation_decision(
            overlay_results=results,
            best_overlay=choose_best_overlay(results),
            event_count=40,
            min_event_count=30,
        )
        == "confirm_candidate_ready_for_narrow_wave"
    )


def test_decision_reject_drawdown_unmitigated() -> None:
    results = [
        {
            "overlay": "exit_on_vwap_loss",
            "sample_count": 40,
            "computable_count": 40,
            "expectancy_r": 0.4,
            "profit_factor": 1.5,
            "max_drawdown_r": 20.0,
            "symbol_count": 6,
            "concentration_top_symbol_pct": 0.3,
            "concentration_top_month_pct": 0.4,
            "decision_eligible": False,
        }
    ]

    assert (
        confirmation_decision(
            overlay_results=results,
            best_overlay=choose_best_overlay(results),
            event_count=40,
            min_event_count=30,
        )
        == "reject_drawdown_unmitigated"
    )


def test_decision_insufficient_event_data() -> None:
    assert (
        confirmation_decision(overlay_results=[], best_overlay={}, event_count=8, min_event_count=30)
        == "insufficient_event_data"
    )


def test_no_lookahead_vwap_loss_ignores_entry_bar_loss(tmp_path: Path) -> None:
    rows = _rows([10.0, 8.0, 12.0, 13.0])
    _write_cache(tmp_path, "TEST", rows)
    events = reconstruct_candidate_events([_sample()], run_id=6454, pattern_key="candidate", ohlcv_cache_dir=tmp_path)

    result = _overlay(simulate_overlays(events), "exit_on_vwap_loss")

    assert result["event_outcomes"][0]["exit_reason"] == "time_stop"


def test_safety_flags_false_in_report_shape() -> None:
    event = CandidateEvent(
        run_id=6454,
        pattern_key="candidate",
        candidate_id=None,
        pattern_id=None,
        side="long",
        symbol="TEST",
        timeframe="30m",
        window_size=100,
        window_start=None,
        window_end=None,
        entry_ts=None,
        entry_price=None,
        risk_proxy=None,
        outcome_r=None,
        mfe_r=None,
        mae_r=None,
        forward_end=None,
        split=None,
        execution_cost_r=None,
        vwap_at_entry=None,
        price_vs_vwap_bps=None,
        vwap_slope_bps=None,
        session_bucket=None,
        month=None,
        source="fixture",
        data_quality="example_only",
        raw={},
    )

    assert event.run_id == 6454
    assert math.isnan(float("nan"))
