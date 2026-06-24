from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from tradeo.modules.intraday.lab_bridge import (
    IntradayLabBridgeThresholds,
    IntradayPaperExitManager,
    IntradayPaperExitPolicy,
    IntradayResearchLabBridge,
)
from tradeo.modules.intraday.research_validation_stack import (
    IntradayValidationResult,
    IntradayValidationThresholds,
)

NOW = datetime(2026, 6, 22, 14, 35, tzinfo=timezone.utc)
FLAT_BY = datetime(2026, 6, 22, 19, 55, tzinfo=timezone.utc)


def _validation(*, accepted: bool = True, net_ev: float = 0.18) -> IntradayValidationResult:
    return IntradayValidationResult(
        accepted=accepted,
        reason_codes=() if accepted else ("research_gate_failed",),
        metrics={
            "effective_events": 80.0,
            "unique_symbols": 12,
            "unique_sessions": 30,
            "unique_buckets": 3,
            "net_expectancy_r": net_ev,
        },
        thresholds=IntradayValidationThresholds(),
    )


def _candidate(**overrides):
    payload = {
        "symbol": "SOUN",
        "pattern_key": "intraday_vwap_reclaim",
        "side": "long",
        "entry": 10.0,
        "stop": 9.5,
        "target": 12.0,
        "score": 0.82,
        "current_price": 10.05,
        "spread_bps": 18.0,
        "spread_cost_r": 0.02,
        "dollar_volume": 2_500_000.0,
        "window_end": NOW.isoformat(),
        "features": {
            "close": 10.05,
            "rvol": 2.1,
            "rvol_acceleration": 0.22,
            "vwap_slope": 0.0015,
            "opening_range_position": 0.95,
            "liquidity_phase_score": 1.0,
        },
    }
    payload.update(overrides)
    return payload


def test_intraday_lab_bridge_allows_paper_only_when_research_timing_and_liquidity_pass() -> None:
    plan = IntradayResearchLabBridge().plan_entry(
        _candidate(),
        _validation(),
        now=NOW,
        flat_by=FLAT_BY,
    )

    assert plan.action == "ENTER_PAPER"
    assert plan.paper_allowed is True
    assert plan.reason_codes == ()
    assert plan.reward_risk == 4.0
    assert plan.opportunity_score >= 0.60
    assert plan.metadata["paper_only"] is True


def test_intraday_lab_bridge_shadows_research_reject_and_rejects_bad_execution_quality() -> None:
    bridge = IntradayResearchLabBridge()
    shadow = bridge.plan_entry(_candidate(), _validation(accepted=False), now=NOW, flat_by=FLAT_BY)
    rejected = bridge.plan_entry(
        _candidate(spread_bps=90.0, dollar_volume=100_000.0),
        _validation(),
        now=NOW,
        flat_by=FLAT_BY,
    )

    assert shadow.action == "SHADOW_ONLY"
    assert "research_validation_not_accepted" in shadow.reason_codes
    assert rejected.action == "REJECT"
    assert "spread_too_wide" in rejected.reason_codes
    assert "low_dollar_volume" in rejected.reason_codes


def test_intraday_lab_bridge_waits_on_weak_timing_without_paper_order() -> None:
    plan = IntradayResearchLabBridge(
        IntradayLabBridgeThresholds(min_opportunity_score=0.50, min_timing_score=0.70)
    ).plan_entry(
        _candidate(features={"close": 10.02, "rvol": 1.1, "rvol_acceleration": -0.30, "vwap_slope": -0.001}),
        _validation(),
        now=NOW,
        flat_by=FLAT_BY,
    )

    assert plan.action == "WAIT"
    assert "timing_score_below_lab_min" in plan.reason_codes
    assert plan.paper_allowed is False


def _bars(values: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    idx = pd.date_range("2026-06-22 14:00", periods=len(values), freq="5min", tz="UTC")
    return pd.DataFrame(values, columns=["open", "high", "low", "close"], index=idx).assign(volume=100_000)


def test_intraday_paper_exit_manager_exits_on_profit_giveback() -> None:
    bars = _bars(
        [
            (10.0, 10.3, 9.95, 10.25),
            (10.25, 10.9, 10.2, 10.85),
            (10.85, 10.9, 10.25, 10.35),
        ]
    )

    decision = IntradayPaperExitManager().decide(
        bars,
        symbol="SOUN",
        side="long",
        entry=10.0,
        stop=9.5,
        target=12.0,
        opened_at=bars.index[0].to_pydatetime(),
        now=bars.index[-1].to_pydatetime(),
        must_close_by=FLAT_BY,
        max_holding_bars=10,
    )

    assert decision.action == "EXIT_NOW"
    assert decision.reason_codes == ("profit_giveback",)
    assert decision.mfe_r > 1.0
    assert decision.should_exit is True


def test_intraday_paper_exit_manager_tightens_then_forces_flat() -> None:
    bars = _bars(
        [
            (10.0, 10.2, 9.95, 10.15),
            (10.15, 10.55, 10.1, 10.50),
        ]
    )
    manager = IntradayPaperExitManager(IntradayPaperExitPolicy(force_exit_minutes_to_flat=3.0))
    tighten = manager.decide(
        bars,
        symbol="SOUN",
        side="long",
        entry=10.0,
        stop=9.5,
        target=12.0,
        opened_at=bars.index[0].to_pydatetime(),
        now=bars.index[-1].to_pydatetime(),
        must_close_by=FLAT_BY,
        max_holding_bars=10,
    )
    forced = manager.decide(
        bars,
        symbol="SOUN",
        side="long",
        entry=10.0,
        stop=9.5,
        target=12.0,
        opened_at=bars.index[0].to_pydatetime(),
        now=FLAT_BY - timedelta(minutes=2),
        must_close_by=FLAT_BY,
        max_holding_bars=10,
    )

    assert tighten.action == "TIGHTEN_STOP"
    assert tighten.suggested_stop is not None
    assert forced.action == "EXIT_NOW"
    assert forced.reason_codes == ("force_flat_window",)
