from __future__ import annotations

import pandas as pd

from tradeo.core.config import Settings
from tradeo.schemas import PatternCandidate
from tradeo.services.backtester import Backtester
from tradeo.services.self_improvement import SelfImprovementEngine


def _candidate() -> PatternCandidate:
    return PatternCandidate(
        symbol="TST",
        entry=100.0,
        stop=95.0,
        target=110.0,
        reward_risk=2.0,
        confidence=0.9,
        rule_score=0.9,
        ml_score=0.9,
        vision_score=0.9,
        composite_score=0.9,
        features={"avg_dollar_volume": 50_000_000.0},
    )


def test_backtester_uses_canonical_both_touch_stop_first() -> None:
    future = pd.DataFrame(
        {"open": [100.0], "high": [112.0], "low": [94.0], "close": [108.0]},
        index=pd.date_range("2024-01-02", periods=1, freq="B"),
    )
    trade = Backtester(provider=object())._simulate_exit("TST", future, _candidate(), entry=100.0)
    assert trade is not None
    assert trade.outcome == "stop_and_target_conservative"
    assert trade.exit == 95.0
    assert trade.r_multiple < -1.0


def test_backtester_gap_past_target_entry_is_skipped() -> None:
    future = pd.DataFrame(
        {"open": [111.0], "high": [112.0], "low": [110.0], "close": [111.0]},
        index=pd.date_range("2024-01-02", periods=1, freq="B"),
    )
    trade = Backtester(provider=object())._simulate_exit("TST", future, _candidate(), entry=111.0)
    assert trade is None


def test_self_improvement_blocks_when_pbo_unavailable(tmp_path) -> None:
    engine = SelfImprovementEngine(
        Settings(
            reports_dir=str(tmp_path),
            self_improvement_min_pbo_blocks=16,
        )
    )
    records = [
        {
            "config": {"min_depth": 0.10},
            "metrics": {
                "total_trades": 40,
                "profit_factor": 2.0,
                "expectancy_r": 0.3,
                "max_drawdown_pct": 5.0,
                "trades": [{"exit_date": "2024-01-01", "r_multiple": 1.0}],
            },
        }
    ]
    guards, summary = engine._anti_overfit_guards(records)
    assert summary["blocked"] is True
    assert guards[0]["pbo_passed"] is False
    assert engine._passes_lab_gate(records[0]["metrics"], guards[0]) is False
