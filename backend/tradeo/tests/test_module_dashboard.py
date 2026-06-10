from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import Signal, SignalStatus, Trade, TradeStatus
from tradeo.db.session import Base
from tradeo.routers.laboratory import laboratory_overview
from tradeo.services.evidence import EvidenceQuality, EvidenceType, FillProvenance
from tradeo.services.module_dashboard import module_overview


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def test_legacy_ibkr_paper_research_trades_are_laboratory_history() -> None:
    db = session_factory()
    signal = Signal(
        symbol="TMDX",
        pattern="research_match_364",
        side="short",
        entry=69.43,
        stop=75.43,
        target=45.43,
        reward_risk=4.0,
        confidence=0.55,
        composite_score=0.55,
        risk_usd=30.0,
        suggested_qty=5,
        strategy_version="ibkr_paper_research_v1",
        status=SignalStatus.EXECUTED,
        human_approved=True,
        metadata_json={"source": "research_current_match"},
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="TMDX",
            pattern="research_match_364",
            side="short",
            qty=5,
            entry=71.67,
            stop=75.43,
            target=45.43,
            status=TradeStatus.OPEN,
            metadata_json={"execution_mode": "paper"},
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")
    fox = module_overview(db, "fox_hunter")

    assert [trade["symbol"] for trade in lab["trades"]] == ["TMDX"]
    assert lab["stats"]["open_trades"] == 1
    assert lab["signals"][0]["status"] == "executed"
    assert lab["signals"][0]["execution_reason_code"] == "trade_open"
    assert lab["trades"][0]["status"] == "open"
    assert fox["trades"] == []


def test_module_overview_exposes_dashboard_data_scope() -> None:
    db = session_factory()

    lab = module_overview(db, "laboratory", limit=12)

    assert lab["data_scope"] == "last_500_query/limit_12"
    assert lab["query_limit"] == 500
    assert lab["summary_limit"] == 12
    assert lab["pnl_basis"] == "operational_fills_only"
    assert lab["stats"]["pnl_basis"] == "operational_fills_only"
    assert lab["director_source"] is False
    assert "Director review" in lab["scope_note"]


def test_laboratory_overview_api_exposes_default_dashboard_data_scope() -> None:
    db = session_factory()

    lab = laboratory_overview("admin", db)

    assert lab["data_scope"] == "last_500_query/limit_80"
    assert lab["query_limit"] == 500
    assert lab["summary_limit"] == 80
    assert lab["pnl_basis"] == "operational_fills_only"
    assert lab["director_source"] is False


def test_legacy_ibkr_paper_smoke_order_is_laboratory_history() -> None:
    db = session_factory()
    signal = Signal(
        symbol="AAPL",
        pattern="ibkr_paper_smoke_test",
        side="long",
        entry=280.0,
        stop=270.0,
        target=330.0,
        reward_risk=5.0,
        confidence=1.0,
        composite_score=1.0,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version="ibkr_smoke_test",
        status=SignalStatus.EXECUTED,
        human_approved=True,
        metadata_json={"purpose": "ibkr_paper_smoke_test"},
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="AAPL",
            pattern="ibkr_paper_smoke_test",
            side="long",
            qty=1,
            entry=280.0,
            stop=270.0,
            target=330.0,
            status=TradeStatus.OPEN,
            metadata_json={"execution_mode": "ibkr", "ibkr_mode": "paper"},
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert [trade["symbol"] for trade in lab["trades"]] == ["AAPL"]
    assert lab["stats"]["open_trades"] == 1
    assert lab["signals"][0]["status"] == "order_submitted"
    assert lab["signals"][0]["next_action"] == "monitor_order_fill"
    assert lab["trades"][0]["status"] == "open"


def test_cancelled_paper_trade_is_signal_status_not_operation() -> None:
    db = session_factory()
    signal = Signal(
        symbol="CALM",
        pattern="research_match_292",
        side="long",
        entry=75.65,
        stop=72.74,
        target=87.26,
        reward_risk=4.0,
        confidence=0.55,
        composite_score=0.55,
        risk_usd=30.0,
        suggested_qty=10,
        strategy_version="ibkr_paper_research_v1",
        status=SignalStatus.EXECUTED,
        human_approved=True,
        metadata_json={"source": "research_current_match"},
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="CALM",
            pattern="research_match_292",
            side="long",
            qty=10,
            entry=75.65,
            stop=72.74,
            target=87.26,
            status=TradeStatus.CANCELLED,
            metadata_json={"execution_mode": "ibkr", "ibkr_mode": "paper", "analysis_exclude": True},
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert lab["trades"] == []
    assert lab["stats"]["trades"] == 0
    assert lab["signals"][0]["symbol"] == "CALM"
    assert lab["signals"][0]["status"] == "order_cancelled"
    assert lab["signals"][0]["execution_reason_code"] == "order_cancelled"
    assert lab["signals"][0]["retryable"] is True


def test_closed_trade_keeps_signal_executed_and_operation_closed() -> None:
    db = session_factory()
    signal = Signal(
        symbol="TMDX",
        pattern="research_match_364",
        side="short",
        entry=69.43,
        stop=75.43,
        target=45.43,
        reward_risk=4.0,
        confidence=0.55,
        composite_score=0.55,
        risk_usd=30.0,
        suggested_qty=5,
        strategy_version="ibkr_paper_research_v1",
        status=SignalStatus.EXECUTED,
        human_approved=True,
        metadata_json={"source": "research_current_match"},
    )
    db.add(signal)
    db.flush()
    db.add(
        Trade(
            signal_id=signal.id,
            symbol="TMDX",
            pattern="research_match_364",
            side="short",
            qty=5,
            entry=71.67,
            stop=75.43,
            target=45.43,
            status=TradeStatus.CLOSED,
            pnl_usd=-30.0,
            r_multiple=-1.0,
            metadata_json={
                "execution_mode": "paper",
                "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
                "broker_fill_id": "test-fill-1",
                "broker_execution_time": "2026-06-10T00:00:00+00:00",
                "commission_usd": 1.0,
            },
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert lab["signals"][0]["status"] == "executed"
    assert lab["trades"][0]["status"] == "closed"
    assert lab["stats"]["open_trades"] == 0
    assert lab["stats"]["closed_trades"] == 1


def test_unsubmitted_signal_keeps_approval_status_for_module_dashboard() -> None:
    db = session_factory()
    db.add(
        Signal(
            symbol="FRPT",
            pattern="research_match_292",
            side="long",
            entry=75.65,
            stop=72.74,
            target=87.26,
            reward_risk=4.0,
            confidence=0.55,
            composite_score=0.55,
            risk_usd=30.0,
            suggested_qty=10,
            strategy_version="laboratory_pattern_292",
            status=SignalStatus.PAPER_APPROVED,
            metadata_json={
                "entry_module": "laboratory",
                "entry_quality": {
                    "score": 0.72,
                    "label": "actionable",
                    "actionable": True,
                    "flags": [],
                },
                "signal_snapshot": {"symbol": "FRPT", "risk": {"approved": True}},
            },
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert lab["trades"] == []
    assert lab["signals"][0]["status"] == "paper_approved"
    assert lab["signals"][0]["execution_reason_code"] == "not_submitted"
    assert lab["signals"][0]["retryable"] is False
    assert lab["signals"][0]["next_action"] == "wait_for_execution_approval"
    assert lab["signals"][0]["entry_quality_score"] == 0.72
    assert lab["signals"][0]["entry_quality_label"] == "actionable"
    assert lab["signals"][0]["signal_snapshot"]["symbol"] == "FRPT"
    assert lab["stats"]["funnel"]["detected"] == 1
    assert lab["stats"]["funnel"]["actionable"] == 1
    assert lab["pattern_outcomes"][0]["pattern"] == "research_match_292"
    assert lab["pattern_outcomes"][0]["signals"] == 1
    assert lab["pattern_outcomes"][0]["actionable"] == 1
    assert lab["pattern_outcomes"][0]["top_reason_code"] == "not_submitted"


def test_approved_signal_without_trade_is_retryable_for_module_dashboard() -> None:
    db = session_factory()
    db.add(
        Signal(
            symbol="FRPT",
            pattern="research_match_292",
            side="long",
            entry=75.65,
            stop=72.74,
            target=87.26,
            reward_risk=4.0,
            confidence=0.55,
            composite_score=0.55,
            risk_usd=30.0,
            suggested_qty=10,
            strategy_version="laboratory_pattern_292",
            status=SignalStatus.PAPER_APPROVED,
            human_approved=True,
            metadata_json={"entry_module": "laboratory"},
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert lab["trades"] == []
    assert lab["signals"][0]["status"] == "retry_order_submission"
    assert lab["signals"][0]["execution_reason_code"] == "no_trade_recorded"
    assert lab["signals"][0]["retryable"] is True


def test_expired_signal_is_discarded_not_retried_for_module_dashboard() -> None:
    db = session_factory()
    db.add(
        Signal(
            symbol="FRPT",
            pattern="research_match_292",
            side="long",
            entry=75.65,
            stop=72.74,
            target=87.26,
            reward_risk=4.0,
            confidence=0.55,
            composite_score=0.55,
            risk_usd=30.0,
            suggested_qty=10,
            strategy_version="laboratory_pattern_292",
            status=SignalStatus.EXPIRED,
            human_approved=True,
            metadata_json={"entry_module": "laboratory"},
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert lab["signals"][0]["status"] == "entry_expired"
    assert lab["signals"][0]["execution_reason_code"] == "entry_price_missed_or_signal_expired"
    assert lab["signals"][0]["retryable"] is False
    assert lab["signals"][0]["next_action"] == "discard_signal"


def test_shadow_closed_trade_is_separated_from_execution_pnl() -> None:
    db = session_factory()
    signal = Signal(
        symbol="SHDW",
        pattern="research_match_shadow",
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.55,
        composite_score=0.55,
        risk_usd=30.0,
        suggested_qty=10,
        strategy_version="laboratory_pattern_1",
        status=SignalStatus.WATCHLIST,
        metadata_json={
            "entry_module": "laboratory",
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
            pattern="research_match_shadow",
            side="long",
            qty=10,
            entry=10.0,
            stop=9.0,
            target=14.0,
            status=TradeStatus.CLOSED,
            pnl_usd=999.0,
            r_multiple=9.99,
            metadata_json={
                "evidence_type": EvidenceType.NEAR_MISS_SHADOW.value,
                "near_miss": True,
                "no_ibkr_order": True,
                "observation_only": True,
            },
        )
    )
    db.commit()

    lab = module_overview(db, "laboratory")

    assert lab["stats"]["closed_trades"] == 0
    assert lab["stats"]["all_closed_trades"] == 1
    assert lab["stats"]["execution_closed_trades"] == 0
    assert lab["stats"]["near_miss_closed_trades"] == 1
    assert lab["stats"]["shadow_closed_trades"] == 0
    assert lab["stats"]["shadow_only"] is True
    assert lab["stats"]["total_pnl_usd"] == 0.0
    assert lab["stats"]["total_r"] == 0
    assert lab["trades"][0]["counts_as_execution_fill"] is False
    assert lab["pattern_outcomes"][0]["near_miss_closed"] == 1
    assert lab["pattern_outcomes"][0]["shadow_closed"] == 0
    assert lab["pattern_outcomes"][0]["total_pnl_usd"] == 0.0
