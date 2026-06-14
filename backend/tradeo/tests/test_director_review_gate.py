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
from tradeo.services.director_review_gate import DirectorProductionGate, DirectorReviewGate
from tradeo.services.evidence import EvidenceQuality, EvidenceType, FillProvenance
from tradeo.services.pattern_health_monitor import PatternHealthMonitor


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
    signal_metadata: dict | None = None,
    trade_metadata: dict | None = None,
) -> None:
    trade_time = datetime(2026, 1, 5, 16, 0, tzinfo=timezone.utc) + timedelta(days=index)
    metadata = {
        "entry_module": "laboratory",
        "pattern_id": pattern.id,
        "entry_variant_id": entry_variant_id,
        "regime": {"regime_key": regime_key} if regime_key else {},
    }
    metadata.update(signal_metadata or {})
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
        metadata_json=metadata,
    )
    db.add(signal)
    db.flush()
    trade_meta = {
        "execution_mode": "ibkr",
        "ibkr_mode": "paper",
        "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
        "evidence_quality": EvidenceQuality.NORMAL.value,
        "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
        "broker_execution_hash": f"broker-execution-hash-{index}",
        "broker_execution_time": trade_time.isoformat(),
        "commission": 0.0,
    }
    trade_meta.update(trade_metadata or {})
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
            evidence_type=trade_meta.get("evidence_type"),
            evidence_quality=trade_meta.get("evidence_quality"),
            metadata_json=trade_meta,
        )
    )
    db.commit()


def production_contract_metrics(*, nested: bool = True) -> dict:
    metrics = {
        "director_gate_status": "passed",
        "director_gate": {"status": "passed", "blockers": []},
        "event_ledger_sha256": "event-ledger-hash",
        "production_evidence_packet": {"id": "packet-1", "hash": "packet-hash"},
        "execution_provenance": {
            "costs_reconciled": True,
            "slippage_reconciled": True,
            "fills_reconciled": True,
        },
        "edge_claim": "NO_DEMOSTRADO",
        "global_experiment_registry": {
            "path": "reports/research/global_experiment_registry.json",
            "registry_hash": "registry-hash",
            "previous_registry_hash": "previous-registry-hash",
            "run_manifest_hash": "run-manifest-hash",
            "hash_chain_valid": True,
        },
    }
    if nested:
        metrics["nested_discovery_replay"] = {
            "status": "passed",
            "implemented": True,
            "passed": True,
            "blocking": False,
        }
    return metrics


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


def test_director_production_gate_blocks_missing_nested_replay_contract() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    pattern.metrics_json = production_contract_metrics(nested=False)
    db.add(pattern)
    db.commit()
    for index in range(3):
        add_closed_lab_trade(db, pattern, index)

    closed_trades = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).all()
    result = DirectorProductionGate(
        min_paper_fills=3,
        min_fill_symbols=1,
        min_fill_trading_days=1,
        min_expectancy_r=0.0,
        min_profit_factor=0.1,
    ).evaluate_pattern(pattern, closed_trades)

    assert result["approved_for_production"] is False
    assert "nested_discovery_replay_missing" in result["blockers"]
    assert result["scientific_contracts"]["director_gate_passed"] is True


def test_director_review_gate_marks_candidate_after_ten_closed_lab_trades() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(10):
        add_closed_lab_trade(db, pattern, index, r_multiple=1.0 if index < 7 else -1.0)

    result = DirectorReviewGate(min_closed_lab_trades=10, min_effective_lab_trades=10).refresh(db)
    db.refresh(pattern)

    assert result["marked_for_director_review"] == 1
    assert pattern.status == DiscoveredPatternStatus.DIRECTOR_REVIEW
    assert pattern.promotion_status == "director_review"
    assert "not production approval" in pattern.promotion_reason
    assert pattern.metrics_json["lab_execution"]["eligible_for_director_review"] is True
    assert pattern.metrics_json["lab_execution"]["lab_expectancy_r"] == 0.4
    assert pattern.metrics_json["lab_execution"]["research_expectancy_r"] == 0.4
    assert pattern.metrics_json["lab_execution"]["unique_lab_symbols"] == 10
    assert pattern.metrics_json["lab_execution"]["unique_lab_days"] == 10
    assert pattern.metrics_json["lab_execution"]["trades_remaining_for_director_review"] == 0
    assert pattern.metrics_json["lab_execution"]["director_review_trigger_trades"] == 10
    sequential = pattern.metrics_json["lab_execution"]["sequential_evaluation"]
    assert sequential["msprt"]["method"] == "normal_mixture_sprt_v1"
    assert sequential["alpha_spending"]["method"] == "alpha_spending_sequential_mean_v1"
    assert sequential["alpha_spending"]["diagnostic_only"] is True


def test_director_review_gate_blocks_until_effective_lab_trade_minimum() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(10):
        add_closed_lab_trade(db, pattern, index, r_multiple=1.0)

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert result["marked_for_director_review"] == 0
    assert pattern.status == DiscoveredPatternStatus.LAB_CANDIDATE
    assert lab_execution["closed_lab_trades"] == 10
    assert lab_execution["effective_lab_trades"] == 10
    assert lab_execution["min_effective_lab_trades"] == 25
    assert "effective_lab_trades_below_25" in lab_execution["promotion_blockers"]


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


def test_director_review_gate_ignores_shadow_and_near_miss_no_order_observations() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(10):
        near_miss = index % 2 == 0
        add_closed_lab_trade(
            db,
            pattern,
            index,
            trade_metadata={
                "execution_mode": "lab_shadow_observation",
                "evidence_type": (
                    EvidenceType.NEAR_MISS_SHADOW.value
                    if near_miss
                    else EvidenceType.SHADOW_NO_ORDER.value
                ),
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "observation_only": True,
                "no_ibkr_order": True,
                "near_miss": near_miss,
                "near_miss_shadow": near_miss,
            },
            signal_metadata={
                "paper_only": True,
                "no_ibkr_order": True,
                "near_miss": near_miss,
                "near_miss_shadow": near_miss,
            },
        )

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert result["marked_for_director_review"] == 0
    assert pattern.status == DiscoveredPatternStatus.LAB_CANDIDATE
    assert lab_execution["closed_lab_trades"] == 0
    assert lab_execution["excluded_lab_evidence_trades"] == 10
    assert lab_execution["excluded_evidence_type_counts"] == {
        EvidenceType.NEAR_MISS_SHADOW.value: 5,
        EvidenceType.SHADOW_NO_ORDER.value: 5,
    }
    assert "closed_lab_trades_below_10" in lab_execution["promotion_blockers"]


def test_director_review_gate_ignores_degraded_fallback_evidence() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(9):
        add_closed_lab_trade(db, pattern, index)
    add_closed_lab_trade(
        db,
        pattern,
        9,
        trade_metadata={
            "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
            "evidence_quality": EvidenceQuality.DEGRADED.value,
            "fallback_used": True,
            "fallback_source": "signal.metadata_json.signal_snapshot.features.last_close",
        },
    )

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert result["marked_for_director_review"] == 0
    assert lab_execution["closed_lab_trades"] == 9
    assert lab_execution["excluded_lab_evidence_trades"] == 1
    assert lab_execution["excluded_evidence_quality_counts"] == {
        EvidenceQuality.DEGRADED.value: 1,
    }
    assert lab_execution["trades_remaining_for_director_review"] == 1


def test_director_review_gate_does_not_promote_closed_paper_order_without_real_fill() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(9):
        add_closed_lab_trade(db, pattern, index)
    add_closed_lab_trade(
        db,
        pattern,
        9,
        trade_metadata={
            "evidence_type": EvidenceType.IBKR_PAPER_ORDER.value,
            "evidence_quality": EvidenceQuality.NORMAL.value,
            "fill_provenance": FillProvenance.SIMULATED_CLOSE.value,
        },
    )

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]

    assert result["marked_for_director_review"] == 0
    assert lab_execution["closed_lab_trades"] == 9
    assert lab_execution["excluded_lab_evidence_trades"] == 1
    assert lab_execution["excluded_evidence_type_counts"] == {
        EvidenceType.IBKR_PAPER_ORDER.value: 1,
    }


def test_director_review_gate_counts_broker_execution_fill_with_hash() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_closed_lab_trade(db, pattern, 0)
    trade = db.query(Trade).one()

    assert DirectorReviewGate._counts_as_paper_fill(trade) is True


def test_director_review_gate_rejects_shadow_close_provenance() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_closed_lab_trade(
        db,
        pattern,
        0,
        trade_metadata={
            "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
            "evidence_quality": EvidenceQuality.NORMAL.value,
            "fill_provenance": FillProvenance.SHADOW_CLOSE.value,
            "broker_execution_hash": "shadow-hash",
            "broker_execution_time": "2026-01-05T16:30:00+00:00",
            "commission": 0.0,
        },
    )
    trade = db.query(Trade).one()

    assert DirectorReviewGate._counts_as_paper_fill(trade) is False


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


def test_director_review_gate_excludes_shadow_near_miss_and_degraded_fallback() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(9):
        add_closed_lab_trade(db, pattern, index, r_multiple=1.0)

    trade_time = datetime(2026, 2, 1, 16, 0, tzinfo=timezone.utc)
    signal = Signal(
        symbol="SHDW",
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
        human_approved=False,
        metadata_json={
            "entry_module": "laboratory",
            "pattern_id": pattern.id,
            "evidence_type": EvidenceType.NEAR_MISS_SHADOW.value,
            "near_miss": True,
            "no_ibkr_order": True,
            "observation_only": True,
        },
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="SHDW",
            pattern=pattern.name,
            side="long",
            qty=1,
            entry=10.0,
            stop=9.0,
            target=14.0,
            status=TradeStatus.CLOSED,
            opened_at=trade_time,
            closed_at=trade_time + timedelta(minutes=30),
            pnl_usd=100.0,
            r_multiple=10.0,
            metadata_json={
                "evidence_type": EvidenceType.NEAR_MISS_SHADOW.value,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "no_ibkr_order": True,
                "observation_only": True,
                "near_miss": True,
            },
        )
    )
    db.commit()

    result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)

    assert result["marked_for_director_review"] == 0
    assert pattern.metrics_json["lab_execution"]["paper_fill_trades"] == 9
    assert pattern.metrics_json["lab_execution"]["closed_lab_trades"] == 9
    assert "closed_lab_trades_below_10" in pattern.metrics_json["lab_execution"]["promotion_blockers"]
    assert pattern.status == DiscoveredPatternStatus.LAB_CANDIDATE


def add_research_skip_accounting(db, pattern: DiscoveredPattern, skip_rate: float = 0.4) -> None:
    skipped = int(round(50 * skip_rate))
    pattern.best_rr = 2.0
    pattern.rr_metrics_json = {
        "2": {
            "rr": 2.0,
            "expectancy_r": 0.5,
            "profit_factor": 2.2,
            "sample_count": 50 - skipped,
            "signal_count": 50,
            "skipped_count": skipped,
            "skip_rate": skip_rate,
            "skip_reason_counts": {"gap_entry_policy": skipped},
        }
    }
    db.add(pattern)
    db.commit()


def test_director_review_gate_surfaces_high_research_skip_rate_evidence() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_research_skip_accounting(db, pattern, skip_rate=0.4)
    for index in range(10):
        add_closed_lab_trade(db, pattern, index, r_multiple=1.0 if index < 7 else -1.0)

    result = DirectorReviewGate(min_closed_lab_trades=10, min_effective_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]
    skip_accounting = lab_execution["research_skip_accounting"]

    # Good expectancy + high skip_rate stays visible but never blocks the gate.
    assert result["marked_for_director_review"] == 1
    assert lab_execution["promotion_blockers"] == []
    assert skip_accounting["available"] is True
    assert skip_accounting["source"] == "pattern.rr_metrics_json[2]"
    assert skip_accounting["skip_rate"] == 0.4
    assert skip_accounting["signal_count"] == 50
    assert skip_accounting["skipped_count"] == 20
    assert skip_accounting["skip_reason_counts"] == {"gap_entry_policy": 20}
    assert lab_execution["research_skip_rate_warning"] is True
    assert lab_execution["skip_rate_warning_threshold"] == 0.25
    warning = next(
        recommendation
        for recommendation in lab_execution["director_recommendations"]
        if recommendation["action"] == "review_research_skip_rate"
    )
    assert warning["priority"] == "high"
    assert warning["skip_rate"] == 0.4
    assert warning["skip_reason_counts"] == {"gap_entry_policy": 20}


def test_director_review_gate_reports_missing_skip_accounting_without_inventing_data() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    for index in range(9):
        add_closed_lab_trade(db, pattern, index)

    DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]
    skip_accounting = lab_execution["research_skip_accounting"]

    assert skip_accounting["available"] is False
    assert "no skip accounting" in skip_accounting["reason"]
    assert "skip_rate" not in skip_accounting
    assert lab_execution["research_skip_rate_warning"] is False
    assert all(
        recommendation["action"] != "review_research_skip_rate"
        for recommendation in lab_execution["director_recommendations"]
    )


def test_director_review_gate_reads_backtest_shape_skip_accounting() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    pattern.metrics_json = {
        "backtest": {"total_signals": 50, "skipped_signals": 10, "skip_rate": 0.2}
    }
    db.add(pattern)
    db.commit()
    for index in range(9):
        add_closed_lab_trade(db, pattern, index)

    DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    lab_execution = pattern.metrics_json["lab_execution"]
    skip_accounting = lab_execution["research_skip_accounting"]

    assert skip_accounting["available"] is True
    assert skip_accounting["source"] == "pattern.metrics_json.backtest"
    assert skip_accounting["signal_count"] == 50
    assert skip_accounting["skipped_count"] == 10
    assert skip_accounting["skip_rate"] == 0.2
    # Below the warning threshold: evidence is visible, no warning raised.
    assert lab_execution["research_skip_rate_warning"] is False


def test_director_production_gate_report_includes_research_skip_accounting() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_research_skip_accounting(db, pattern, skip_rate=0.4)
    for index in range(3):
        add_closed_lab_trade(db, pattern, index)

    closed_trades = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).all()
    result = DirectorProductionGate(
        min_paper_fills=3,
        min_fill_symbols=1,
        min_fill_trading_days=1,
        min_expectancy_r=0.0,
        min_profit_factor=0.1,
    ).evaluate_pattern(pattern, closed_trades)
    skip_accounting = result["research_skip_accounting"]

    assert skip_accounting["available"] is True
    assert skip_accounting["skip_rate"] == 0.4
    assert skip_accounting["skip_reason_counts"] == {"gap_entry_policy": 20}
    # Skip accounting is evidence only: it must never appear as a blocker.
    assert all("skip" not in blocker for blocker in result["blockers"])


def test_pattern_health_monitor_marks_decaying_on_shortfall_cusum() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    pattern.status = DiscoveredPatternStatus.DIRECTOR_REVIEW
    db.add(pattern)
    db.commit()
    for index in range(8):
        add_closed_lab_trade(
            db,
            pattern,
            index,
            r_multiple=0.5,
            trade_metadata={
                "entry_fill_price": 10.35,
                "exit_fill_price": 14.0,
                "exit_reason": "target_hit",
            },
        )

    result = PatternHealthMonitor().run(db)
    db.refresh(pattern)

    assert result["decay_detected"] == 1
    assert pattern.drift_status == "decaying"
    health = pattern.metrics_json["pattern_health"]
    assert health["shortfall_fills"] == 8
    assert health["shortfall_cusum"]["available"] is True
    assert health["shortfall_cusum"]["triggered"] is True
