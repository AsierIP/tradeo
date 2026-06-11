from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import Signal, SignalStatus, Trade, TradeStatus
from tradeo.db.session import Base
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


def test_position_size_respects_adv_participation_cap() -> None:
    candidate = PatternCandidate(
        symbol="TEST",
        entry=10.0,
        stop=9.99,
        target=10.04,
        reward_risk=4.0,
        confidence=0.8,
        rule_score=0.8,
        ml_score=0.8,
        vision_score=0.8,
        composite_score=0.8,
        features={"avg_dollar_volume": 5_000_000, "atr_pct": 0.04},
    )
    settings = Settings(max_adv_participation_pct=0.0001)

    decision = RiskManager(settings).validate_candidate(candidate)

    assert decision.approved
    assert decision.suggested_qty == 50
    assert "adv_participation_cap_reduced_qty_to_50" in decision.warnings


def test_rejects_when_pattern_family_position_cap_reached() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, future=True)()
    signal = Signal(
        symbol="AAA",
        pattern="PATTERN_A",
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.8,
        composite_score=0.8,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version="laboratory_pattern_1",
        status=SignalStatus.EXECUTED,
        metadata_json={"pattern_family_key": "family-a"},
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="AAA",
            pattern="PATTERN_A",
            side="long",
            qty=1,
            entry=10.0,
            stop=9.0,
            target=14.0,
            status=TradeStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            metadata_json={"execution_mode": "ibkr"},
        )
    )
    db.commit()
    candidate = PatternCandidate(
        symbol="BBB",
        entry=10.0,
        stop=9.5,
        target=12.0,
        reward_risk=4.0,
        confidence=0.8,
        rule_score=0.8,
        ml_score=0.8,
        vision_score=0.8,
        composite_score=0.8,
        features={"avg_dollar_volume": 10_000_000, "atr_pct": 0.04, "pattern_family_key": "family-a"},
    )

    decision = RiskManager(Settings(max_open_positions_per_pattern_family=1)).validate_candidate(
        candidate,
        db,
    )

    assert not decision.approved
    assert "pattern_family_position_cap_1_reached" in decision.hard_rejections
