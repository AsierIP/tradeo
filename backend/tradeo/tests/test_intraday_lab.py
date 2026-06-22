from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from tradeo.modules.intraday.lab import IntradayLabObservationService


def _bars() -> pd.DataFrame:
    idx = pd.date_range("2026-06-22 14:00", periods=4, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [10.0, 10.2, 10.5, 10.9],
            "high": [10.3, 10.6, 11.0, 12.1],
            "low": [9.9, 10.1, 10.4, 10.8],
            "close": [10.2, 10.5, 10.9, 12.0],
            "volume": [100, 120, 150, 200],
        },
        index=idx,
    )


def test_intraday_lab_shadow_observation_hits_target_without_broker() -> None:
    observation = IntradayLabObservationService().observe(
        _bars(),
        symbol="soun",
        side="long",
        entry=10.0,
        stop=9.5,
        target=12.0,
        opened_at=datetime(2026, 6, 22, 14, 0, tzinfo=timezone.utc),
        must_close_by=datetime(2026, 6, 22, 20, 0, tzinfo=timezone.utc),
        max_holding_bars=4,
        estimated_cost_r=0.1,
    )

    assert observation.shadow_only is True
    assert observation.exit_reason == "target"
    assert observation.outcome_r == 3.9
    assert observation.mfe_r >= 4.0
    assert observation.eligible_evidence is True


def test_intraday_lab_does_not_cross_session_boundary() -> None:
    observation = IntradayLabObservationService().observe(
        _bars(),
        symbol="soun",
        side="long",
        entry=10.0,
        stop=9.5,
        target=12.0,
        opened_at=datetime(2026, 6, 22, 14, 0, tzinfo=timezone.utc),
        must_close_by=datetime(2026, 6, 22, 14, 5, tzinfo=timezone.utc),
        max_holding_bars=10,
    )

    assert observation.bars_held == 2
    assert observation.exit_reason == "intraday_eod_flat"
