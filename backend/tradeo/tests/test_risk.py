from __future__ import annotations

from tradeo.schemas import PatternCandidate
from tradeo.services.risk_manager import RiskManager


def test_position_size_respects_30_usd_risk_budget() -> None:
    candidate = PatternCandidate(
        symbol="TEST",
        entry=10.0,
        stop=9.5,
        target=12.0,
        reward_risk=4.0,
        confidence=0.8,
        rule_score=0.8,
        ml_score=0.8,
        vision_score=0.8,
        composite_score=0.8,
        features={"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
    )
    decision = RiskManager().validate_candidate(candidate)
    assert decision.approved
    assert decision.risk_usd <= 30.01


def test_rejects_reward_risk_below_four() -> None:
    candidate = PatternCandidate(
        symbol="TEST",
        entry=10.0,
        stop=9.5,
        target=11.0,
        reward_risk=2.0,
        confidence=0.8,
        rule_score=0.8,
        ml_score=0.8,
        vision_score=0.8,
        composite_score=0.8,
        features={"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
    )
    decision = RiskManager().validate_candidate(candidate)
    assert not decision.approved
    assert any("reward_risk" in x for x in decision.hard_rejections)
