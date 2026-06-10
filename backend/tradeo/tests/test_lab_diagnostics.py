from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternMatch,
    DiscoveredPatternStatus,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.db.session import Base
from tradeo.services.evidence import EvidenceQuality, EvidenceType, FillProvenance
from tradeo.services.lab_diagnostics import laboratory_diagnostics


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def add_pattern(db) -> DiscoveredPattern:
    pattern = DiscoveredPattern(
        pattern_key="LAB_DIAG_PATTERN",
        name="LAB_DIAG_PATTERN",
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        promotion_status="lab_candidate",
        validation_passed=True,
        score=0.72,
        expectancy_r=0.22,
        profit_factor=1.7,
        best_expectancy_r=0.35,
        best_profit_factor=2.0,
        metrics_json={
            "lab_execution": {
                "closed_lab_trades": 1,
                "promotion_blockers": ["closed_lab_trades_below_10"],
                "eligible_for_director_review": False,
            }
        },
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


def add_closed_paper_trade(db, pattern: DiscoveredPattern) -> None:
    signal = Signal(
        symbol="LABX",
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
            "entry_variant_id": "next_bar_limit_retest",
            "regime": {"regime_key": "bull_trend_liquid"},
        },
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="LABX",
            pattern=pattern.name,
            side="long",
            qty=1,
            entry=10.0,
            stop=9.0,
            target=14.0,
            status=TradeStatus.CLOSED,
            opened_at=datetime(2026, 6, 8, 15, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 6, 8, 16, 0, tzinfo=timezone.utc),
            pnl_usd=12.0,
            r_multiple=1.2,
            evidence_type=EvidenceType.IBKR_PAPER_FILL.value,
            evidence_quality=EvidenceQuality.NORMAL.value,
            metadata_json={
                "execution_mode": "ibkr",
                "ibkr_mode": "paper",
                "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
                "broker_execution_hash": "lab-diagnostics-fill",
                "broker_execution_time": "2026-06-08T16:00:00+00:00",
                "commission": 0.0,
            },
        )
    )
    db.commit()


def add_closed_shadow_observation(db, pattern: DiscoveredPattern) -> None:
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
            "paper_only": True,
            "no_ibkr_order": True,
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
            opened_at=datetime(2026, 6, 8, 15, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 6, 8, 16, 0, tzinfo=timezone.utc),
            pnl_usd=12.0,
            r_multiple=1.2,
            metadata_json={
                "execution_mode": "lab_shadow_observation",
                "evidence_type": EvidenceType.SHADOW_NO_ORDER.value,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "paper_only": True,
                "no_ibkr_order": True,
                "observation_only": True,
            },
        )
    )
    db.commit()


def test_laboratory_diagnostics_combines_candidates_rejections_and_paper_history() -> None:
    db = session_factory()
    pattern = add_pattern(db)
    add_closed_paper_trade(db, pattern)
    add_closed_shadow_observation(db, pattern)
    entry_gate = {
        "passed": False,
        "trigger": "momentum_close",
        "entry_score": 0.61,
        "volume_ratio": 0.72,
        "volume_confirmed": False,
        "extension_atr": 0.8,
        "not_extended": True,
        "regime_score": 0.7,
        "regime_ok": True,
        "trend_aligned": True,
        "atr_pct": 0.02,
        "volatility_ok": True,
    }
    match = {
        "symbol": "LABX",
        "pattern_id": pattern.id,
        "pattern_name": pattern.name,
        "side": "long",
        "timeframe": "1d",
        "score": 0.7,
        "entry_score": 0.61,
        "similarity": 0.82,
        "entry_variant_id": "next_bar_limit_retest",
        "entry_variant": {"id": "next_bar_limit_retest", "order_style": "next_bar_limit"},
        "regime": {"regime_key": "bull_trend_liquid"},
        "regime_fit": {"score": 0.8, "label": "seen_regime"},
        "opportunity_rank": 1,
        "opportunity_rank_score": 0.74,
        "opportunity_rank_components": {"entry": 0.61, "history_count": 1.0},
        "window_end": "2026-06-08",
        "metrics": {"entry_gate": entry_gate},
    }
    db.add(
        AuditLog(
            actor="laboratory",
            action="entry_match_rejected_by_entry_gate",
            entity_type="discovered_pattern_match",
            entity_id=str(pattern.id),
            details_json={"match": match, "entry_gate": entry_gate},
        )
    )
    db.add(
        Signal(
            symbol="CAND",
            pattern=pattern.name,
            side="long",
            entry=20.0,
            stop=19.0,
            target=24.0,
            reward_risk=4.0,
            confidence=0.8,
            composite_score=0.8,
            risk_usd=10.0,
            suggested_qty=1,
            strategy_version=f"laboratory_pattern_{pattern.id}",
            status=SignalStatus.PAPER_APPROVED,
            metadata_json={
                "entry_module": "laboratory",
                "pattern_id": pattern.id,
                "entry_variant_id": "volume_confirmed_close",
                "entry_gate": {**entry_gate, "passed": True, "volume_confirmed": True},
                "entry_quality": {"score": 0.76, "label": "actionable", "flags": []},
                "opportunity_rank": 2,
                "opportunity_rank_score": 0.68,
            },
        )
    )
    db.add(
        DiscoveredPatternMatch(
            pattern_id=pattern.id,
            symbol="SHDW",
            timeframe="1d",
            side="long",
            similarity=0.8,
            score=0.66,
            status="lab_entry_candidate",
            window_end="2026-06-08",
            metrics_json={
                "entry_variant_id": "next_bar_stop_confirmation",
                "entry_variant": {
                    "id": "next_bar_stop_confirmation",
                    "order_style": "next_bar_stop",
                },
                "entry_gate": entry_gate,
                "regime": {"regime_key": "bull_trend_liquid"},
            },
        )
    )
    db.commit()

    diagnostics = laboratory_diagnostics(db, limit=10)
    rows = diagnostics["opportunities"]
    rejected = next(row for row in rows if row["source"] == "rejected")
    candidate = next(row for row in rows if row["source"] == "candidate_signal")
    shadow = next(row for row in rows if row["source"] == "shadow_match")

    assert diagnostics["summary"]["candidates"] == 1
    assert diagnostics["summary"]["rejected"] == 1
    assert diagnostics["summary"]["shadow_near_misses"] == 1
    assert rejected["rejection_reason"] == "weak_volume_confirmation"
    assert rejected["entry_gate_components"][1]["name"] == "volume"
    assert rejected["entry_gate_components"][1]["ok"] is False
    assert rejected["paper_history"]["closed_trades"] == 1
    assert rejected["paper_history"]["variant_closed_trades"] == 1
    assert rejected["paper_history"]["regime_closed_trades"] == 1
    assert rejected["missing_to_promote"] == ["closed_lab_trades_below_10"]
    assert candidate["rejection_reason"] == "paper_candidate_not_submitted"
    assert shadow["rejection_stage"] == "shadow_near_miss"
