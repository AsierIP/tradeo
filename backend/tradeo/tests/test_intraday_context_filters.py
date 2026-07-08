from __future__ import annotations

import pandas as pd

from tradeo.research.intraday_context_filters import (
    benchmark_regime_filter_passes,
    build_benchmark_regime_frames,
    cost_filter_passes,
    normalize_context_filter_spec,
    session_filter_passes,
)


def test_session_filter_mid_accepts_1030_through_before_1500_ny() -> None:
    spec = normalize_context_filter_spec(session_filter="mid")

    assert session_filter_passes(pd.Timestamp("2026-07-01 10:30", tz="America/New_York"), spec)
    assert session_filter_passes(pd.Timestamp("2026-07-01 14:59", tz="America/New_York"), spec)
    assert not session_filter_passes(pd.Timestamp("2026-07-01 10:29", tz="America/New_York"), spec)
    assert not session_filter_passes(pd.Timestamp("2026-07-01 15:00", tz="America/New_York"), spec)


def test_session_filter_no_close_rejects_close_bucket() -> None:
    spec = normalize_context_filter_spec(session_filter="no_close")

    assert session_filter_passes(pd.Timestamp("2026-07-01 14:59", tz="America/New_York"), spec)
    assert not session_filter_passes(pd.Timestamp("2026-07-01 15:00", tz="America/New_York"), spec)
    assert not session_filter_passes(pd.Timestamp("2026-07-01 15:59", tz="America/New_York"), spec)
    assert session_filter_passes(pd.Timestamp("2026-07-01 16:00", tz="America/New_York"), spec)


def test_low_cost_filter_uses_default_threshold_and_accepts_equal_cost() -> None:
    spec = normalize_context_filter_spec(cost_filter="low_cost")

    assert spec.max_execution_cost_r == 0.15
    assert cost_filter_passes(0.15, spec)
    assert not cost_filter_passes(0.15001, spec)


def test_low_cost_filter_respects_explicit_threshold() -> None:
    spec = normalize_context_filter_spec(cost_filter="low_cost", max_execution_cost_r=0.08)

    assert cost_filter_passes(0.08, spec)
    assert not cost_filter_passes(0.081, spec)


def test_benchmark_regime_filter_requires_spy_and_qqq_positive() -> None:
    spec = normalize_context_filter_spec(benchmark_regime_filter="spy_qqq_positive")
    frames = build_benchmark_regime_frames({"SPY": _benchmark_bars(up=True), "QQQ": _benchmark_bars(up=True)}, spec)

    passed, missing, features = benchmark_regime_filter_passes(
        pd.Timestamp("2026-07-01 11:00", tz="America/New_York"),
        spec,
        frames,
    )

    assert passed is True
    assert missing is False
    assert features["benchmark_regime_states"] == {"SPY": "positive", "QQQ": "positive"}


def test_benchmark_regime_filter_rejects_negative_or_missing_inputs() -> None:
    spec = normalize_context_filter_spec(benchmark_regime_filter="spy_qqq_positive")
    negative_frames = build_benchmark_regime_frames(
        {"SPY": _benchmark_bars(up=False), "QQQ": _benchmark_bars(up=True)},
        spec,
    )

    passed, missing, features = benchmark_regime_filter_passes(
        pd.Timestamp("2026-07-01 11:00", tz="America/New_York"),
        spec,
        negative_frames,
    )
    missing_passed, missing_flag, _ = benchmark_regime_filter_passes(
        pd.Timestamp("2026-07-01 11:00", tz="America/New_York"),
        spec,
        build_benchmark_regime_frames({"SPY": _benchmark_bars(up=True)}, spec),
    )

    assert passed is False
    assert missing is False
    assert features["benchmark_regime_states"]["SPY"] == "negative"
    assert missing_passed is False
    assert missing_flag is True


def test_benchmark_regime_filter_uses_no_future_benchmark_bars() -> None:
    spec = normalize_context_filter_spec(benchmark_regime_filter="spy_qqq_positive")
    base_frames = build_benchmark_regime_frames({"SPY": _benchmark_bars(up=True), "QQQ": _benchmark_bars(up=True)}, spec)
    mutated = _benchmark_bars(up=True)
    mutated.loc[pd.Timestamp("2026-07-01 11:30", tz="America/New_York"), ["open", "high", "low", "close"]] = [
        50.0,
        51.0,
        49.0,
        50.0,
    ]
    future_frames = build_benchmark_regime_frames({"SPY": mutated, "QQQ": _benchmark_bars(up=True)}, spec)
    timestamp = pd.Timestamp("2026-07-01 11:00", tz="America/New_York")

    assert benchmark_regime_filter_passes(timestamp, spec, base_frames) == benchmark_regime_filter_passes(
        timestamp,
        spec,
        future_frames,
    )


def _benchmark_bars(*, up: bool) -> pd.DataFrame:
    index = pd.date_range("2026-07-01 09:30", periods=5, freq="30min", tz="America/New_York")
    closes = [100, 101, 102, 103, 104] if up else [104, 103, 102, 101, 100]
    rows = [
        {
            "open": float(close),
            "high": float(close) + 0.5,
            "low": float(close) - 0.5,
            "close": float(close),
            "volume": 1000.0,
        }
        for close in closes
    ]
    return pd.DataFrame(rows, index=index)
