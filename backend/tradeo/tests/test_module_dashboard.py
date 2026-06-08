from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import Signal, SignalStatus, Trade, TradeStatus
from tradeo.db.session import Base
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
    assert fox["trades"] == []


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
