from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tradeo.modules.intraday.risk import (
    IntradayRiskLimits,
    IntradayRiskManager,
    IntradayRiskRequest,
    IntradayRiskState,
)


NOW = datetime(2026, 6, 22, 15, 0, tzinfo=timezone.utc)


def test_intraday_risk_rejects_entries_after_limits_and_cutoff() -> None:
    manager = IntradayRiskManager(
        IntradayRiskLimits(
            max_trades_per_day=3,
            max_trades_per_symbol=1,
            max_open_positions=2,
            max_daily_loss_usd=100,
            max_notional_usd=5_000,
            max_hold_minutes=60,
            no_new_entries_at=NOW,
        )
    )
    state = IntradayRiskState(
        trades_today=3,
        open_positions=2,
        realized_pnl_usd=-100,
        notional_open_usd=4_900,
        trades_by_symbol={"SOUN": 1},
        cooldown_until_by_symbol={"SOUN": NOW + timedelta(minutes=5)},
    )

    decision = manager.evaluate(
        IntradayRiskRequest(symbol="SOUN", now=NOW, notional_usd=200, expected_hold_minutes=90),
        state,
    )

    assert decision.allowed is False
    assert decision.reason_codes == (
        "no_new_entries_cutoff",
        "max_trades_per_day",
        "max_trades_per_symbol",
        "max_open_positions",
        "max_daily_loss",
        "max_notional",
        "max_hold_minutes",
        "cooldown_active",
    )


def test_intraday_risk_reduce_only_survives_entry_blocks() -> None:
    manager = IntradayRiskManager(IntradayRiskLimits(no_new_entries_at=NOW))
    decision = manager.evaluate(
        IntradayRiskRequest(symbol="SOUN", intent="REDUCE_ONLY", now=NOW + timedelta(minutes=1)),
        IntradayRiskState(stale_data=True),
    )

    assert decision.allowed is True
    assert decision.reduce_only is True
    assert decision.reason_codes == ("stale_data",)


def test_intraday_risk_blocks_reduce_only_on_desync() -> None:
    manager = IntradayRiskManager(IntradayRiskLimits())
    decision = manager.evaluate(
        IntradayRiskRequest(symbol="SOUN", intent="REDUCE_ONLY", now=NOW),
        IntradayRiskState(broker_desync=True),
    )

    assert decision.allowed is False
    assert decision.reason_code == "broker_desync"
