"""Persisted effective-sample weights for Director paper fills (informe §4.7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
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
from tradeo.services.effective_sample import (
    EFFECTIVE_SAMPLE_METHOD,
    effective_sample_summary,
)
from tradeo.services.evidence import EvidenceQuality, EvidenceType, FillProvenance


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


def add_paper_fill(
    db,
    pattern: DiscoveredPattern,
    index: int,
    *,
    symbol: str,
    closed_at: datetime,
    r_multiple: float = 1.0,
) -> None:
    signal = Signal(
        symbol=symbol,
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
        metadata_json={"entry_module": "laboratory", "pattern_id": pattern.id},
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol=symbol,
            pattern=pattern.name,
            side="long",
            qty=1,
            entry=10.0,
            stop=9.0,
            target=14.0,
            status=TradeStatus.CLOSED,
            opened_at=closed_at - timedelta(minutes=30),
            closed_at=closed_at,
            pnl_usd=10.0 * r_multiple,
            r_multiple=r_multiple,
            evidence_type=EvidenceType.IBKR_PAPER_FILL.value,
            evidence_quality=EvidenceQuality.NORMAL.value,
            metadata_json={
                "execution_mode": "ibkr",
                "ibkr_mode": "paper",
                "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
                "broker_execution_hash": f"hash-{index}",
                "broker_execution_time": closed_at.isoformat(),
                "commission": 0.0,
            },
        )
    )
    db.commit()


BASE_TIME = datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc)


def test_same_symbol_same_day_cluster_counts_as_one_effective_sample() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(4):
        add_paper_fill(db, pattern, index, symbol="AAPL", closed_at=BASE_TIME)
    trades = db.query(Trade).all()

    summary = effective_sample_summary(trades)

    assert summary["method"] == EFFECTIVE_SAMPLE_METHOD
    assert summary["n_trades"] == 4
    assert summary["n_eff"] == pytest.approx(1.0)
    # Kish ESS only reflects weight inequality (equal weights -> n); the
    # binding gate number is n_eff.
    assert summary["kish_n_eff"] == pytest.approx(4.0)
    assert summary["cluster_sizes"] == {"AAPL|2026-01-05": 4}
    assert all(entry["weight"] == pytest.approx(0.25) for entry in summary["weights"])


def test_mixed_clusters_report_expected_n_eff_and_kish() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_paper_fill(db, pattern, 0, symbol="MSFT", closed_at=BASE_TIME)
    for index in range(1, 4):
        add_paper_fill(db, pattern, index, symbol="AAPL", closed_at=BASE_TIME)
    trades = db.query(Trade).all()

    summary = effective_sample_summary(trades)

    # Weights are [1, 1/3, 1/3, 1/3]: n_eff = 2 clusters, Kish = 4/(4/3) = 3.
    assert summary["n_eff"] == pytest.approx(2.0)
    assert summary["kish_n_eff"] == pytest.approx(3.0)
    assert summary["cluster_count"] == 2


def test_independent_fills_keep_full_effective_sample() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(5):
        add_paper_fill(
            db,
            pattern,
            index,
            symbol=f"SYM{index}",
            closed_at=BASE_TIME + timedelta(days=index),
        )
    trades = db.query(Trade).all()

    summary = effective_sample_summary(trades)

    assert summary["n_eff"] == pytest.approx(5.0)
    assert summary["kish_n_eff"] == pytest.approx(5.0)


def test_gate_blocks_concentrated_fills_even_above_raw_count_minimum() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    # 25 raw fills, but all on the same symbol and day: one effective sample.
    for index in range(25):
        add_paper_fill(db, pattern, index, symbol="AAPL", closed_at=BASE_TIME)

    gate = DirectorReviewGate(min_closed_lab_trades=10, min_effective_lab_trades=25)
    result = gate.refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert result["marked_for_director_review"] == 0
    assert lab_execution["closed_lab_trades"] == 25
    assert lab_execution["effective_lab_trades"] == pytest.approx(1.0)
    assert "effective_lab_trades_below_25" in lab_execution["promotion_blockers"]
    assert lab_execution["effective_sample"]["method"] == EFFECTIVE_SAMPLE_METHOD
    assert lab_execution["effective_sample"]["n_eff"] == pytest.approx(1.0)


def test_gate_persists_per_trade_weights_in_trade_metadata() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_paper_fill(db, pattern, 0, symbol="MSFT", closed_at=BASE_TIME)
    for index in range(1, 3):
        add_paper_fill(db, pattern, index, symbol="AAPL", closed_at=BASE_TIME)

    DirectorReviewGate().refresh(db)

    trades = db.query(Trade).all()
    for trade in trades:
        record = trade.metadata_json["effective_sample"]
        assert record["method"] == EFFECTIVE_SAMPLE_METHOD
        assert record["computed_at"]
    weights = {
        trade.symbol: trade.metadata_json["effective_sample"]["weight"] for trade in trades
    }
    assert weights["MSFT"] == pytest.approx(1.0)
    assert weights["AAPL"] == pytest.approx(0.5)


def test_gate_accepts_diversified_effective_sample() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(25):
        add_paper_fill(
            db,
            pattern,
            index,
            symbol=f"SYM{index}",
            closed_at=BASE_TIME + timedelta(days=index),
        )

    gate = DirectorReviewGate(min_closed_lab_trades=10, min_effective_lab_trades=25)
    gate.refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert lab_execution["effective_lab_trades"] == pytest.approx(25.0)
    assert "effective_lab_trades_below_25" not in lab_execution["promotion_blockers"]
