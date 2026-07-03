from __future__ import annotations

import pandas as pd

from tradeo.research.intraday_context_filters import (
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
