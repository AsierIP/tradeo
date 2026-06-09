from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import (
    DiscoveredPattern,
    DiscoveredPatternStatus,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.db.session import Base
from tradeo.services.director_review_gate import DirectorReviewGate


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def add_pattern(db) -> DiscoveredPattern:
    pattern = DiscoveredPattern(
        pattern_key="LAB_PATTERN_1",
        name="LAB_PATTERN_1",
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        promotion_status="lab_candidate",
        validation_passed=True,
        expectancy_r=0.25,
        profit_factor=1.8,
        best_expectancy_r=0.4,
        best_profit_factor=2.0,
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


def add_closed_lab_trade(
    db,
    pattern: DiscoveredPattern,
    index: int,
    r_multiple: float = 1.0,
    *,
    symbol: str | None = None,
    entry_variant_id: str | None = None,
    regime_key: str | None = None,
) -> None:
    trade_time = datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc) + timedelta(days=index)
    signal = Signal(
        symbol=symbol or f"T{index}",
        pattern=pattern.name,
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.7,
        composite_score=0.7,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version=f"laboratory_pattern_{pattern.id}",
        status=SignalStatus.EXECUTED,
        human_approved=True,
        metadata_json={
            "entry_module": "laboratory",
            "pattern_id": pattern.id,
            "entry_variant_id": entry_variant_id,
            "regime": {"regime_key": regime_key} if regime_key else {},
        },
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol=signal.symbol,
            pattern=pattern.name,
            side="long",
            qty=1,
            entry=10.0,
            stop=9.0,
            target=14.0,
            status=TradeStatus.CLOSED,
            opened_at=trade_time,
            closed_at=trade_time + timedelta(minutes=30),
            pnl_usd=10.0 * r_multiple,
            r_multiple=r_multiple,
            metadata_json={"execution_mode": "ibkr", "ibkr_mode": "paper"},
        )
    )
    db.commit()


def test_director_review_gate_waits_for_ten_closed_lab_trades() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(9):
        add_closed_lab_trade(db, pattern, index)

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)

    assert result["marked_for_director_review"] == 0
    assert pattern.status == DiscoveredPatternStatus.LAB_CANDIDATE
    assert pattern.metrics_json["lab_execution"]["closed_lab_trades"] == 9
    assert pattern.metrics_json["lab_execution"]["trades_remaining_for_director_review"] == 1
    assert pattern.metrics_json["lab_execution"]["eligible_for_director_review"] is False
    assert "closed_lab_trades_below_10" in pattern.metrics_json["lab_execution"]["promotion_blockers"]
    assert pattern.metrics_json["lab_execution"]["by_regime"]
    assert pattern.metrics_json["lab_execution"]["by_regime_empty_reason"] == ""
    assert pattern.metrics_json["lab_execution"]["director_recommendations"][0]["action"] == "collect_closed_lab_trades"


def test_director_review_gate_marks_candidate_after_ten_closed_lab_trades() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(10):
        add_closed_lab_trade(db, pattern, index, r_multiple=1.0 if index < 7 else -1.0)

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)

    assert result["marked_for_director_review"] == 1
    assert pattern.status == DiscoveredPatternStatus.DIRECTOR_REVIEW
    assert pattern.promotion_status == "director_review"
    assert pattern.metrics_json["lab_execution"]["eligible_for_director_review"] is True
    assert pattern.metrics_json["lab_execution"]["lab_expectancy_r"] == 0.4
    assert pattern.metrics_json["lab_execution"]["research_expectancy_r"] == 0.4
    assert pattern.metrics_json["lab_execution"]["unique_lab_symbols"] == 10
    assert pattern.metrics_json["lab_execution"]["unique_lab_days"] == 10
    assert pattern.metrics_json["lab_execution"]["trades_remaining_for_director_review"] == 0


def test_director_review_gate_blocks_low_diversity_lab_results() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(10):
        add_closed_lab_trade(db, pattern, index, symbol="SAME")

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)

    assert result["marked_for_director_review"] == 0
    assert pattern.status == DiscoveredPatternStatus.LAB_CANDIDATE
    assert pattern.metrics_json["lab_execution"]["eligible_for_director_review"] is False
    assert "unique_lab_symbols_below_3" in pattern.metrics_json["lab_execution"]["promotion_blockers"]


def test_director_review_gate_explains_missing_bucket_data_when_no_trades() -> None:
    db = session_factory()
    pattern = add_pattern(db)

    DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert lab_execution["closed_lab_trades"] == 0
    assert lab_execution["by_entry_variant"] == {}
    assert lab_execution["by_regime"] == {}
    assert "no_closed_lab_trades" in lab_execution["by_entry_variant_empty_reason"]
    assert "no_closed_lab_trades" in lab_execution["by_regime_empty_reason"]
    assert lab_execution["director_recommendations"][0]["trades_remaining"] == 10
    assert lab_execution["director_recommendations"][1]["action"] == "keep_research_only"


def test_director_review_gate_ranks_entry_variant_and_regime_buckets() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(5):
        add_closed_lab_trade(
            db,
            pattern,
            index,
            r_multiple=1.2,
            entry_variant_id="next_bar_limit_retest",
            regime_key="market_up",
        )
    for index in range(5, 10):
        add_closed_lab_trade(
            db,
            pattern,
            index,
            r_multiple=-0.2,
            entry_variant_id="momentum_close",
            regime_key="market_down",
        )

    DirectorReviewGate(
        min_closed_lab_trades=10,
        min_lab_symbols=1,
        min_lab_trading_days=1,
        min_baseline_edge_r=0.0,
        min_lab_profit_factor=0.1,
    ).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert lab_execution["best_entry_variant"]["key"] == "next_bar_limit_retest"
    assert lab_execution["worst_entry_variant"]["key"] == "momentum_close"
    assert lab_execution["best_regime"]["key"] == "market_up"
    assert lab_execution["worst_regime"]["key"] == "market_down"
    assert any(
        recommendation["action"] == "prioritize_entry_variant"
        for recommendation in lab_execution["director_recommendations"]
    )
    assert any(
        recommendation["action"] == "gate_by_regime_until_confirmed"
        for recommendation in lab_execution["director_recommendations"]
    )
