"""Explicit order-state transition and reconciliation tests (informe §4.5).

Covers the trade state machine end to end:
- signal -> trade transitions in the paper broker;
- lab shadow observation lifecycle (open -> closed / pending);
- evidence promotion rules (order -> fill) on status transitions;
- DB <-> broker reconciliation, including the automatic kill switch and the
  broker-unreachable path that must never trip it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import (
    AuditLog,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.db.session import Base
from tradeo.modules.laboratory.paper_observations import LabPaperObservationService
from tradeo.services.evidence import (
    EvidenceQuality,
    EvidenceType,
    FillProvenance,
    evidence_type_for_metadata,
)
from tradeo.services.ibkr_broker import IBKRBroker, IBKRSafetyError
from tradeo.services.paper_broker import PaperBroker
from tradeo.services.reconciliation import ReconciliationService
from tradeo.services.system_controls import (
    activate_runtime_kill_switch,
    deactivate_runtime_kill_switch,
    runtime_kill_switch_active,
)


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def add_signal(db, *, status: SignalStatus, qty: int = 5, symbol: str = "AAPL") -> Signal:
    signal = Signal(
        symbol=symbol,
        pattern="cup_handle",
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.7,
        composite_score=0.7,
        risk_usd=10.0,
        suggested_qty=qty,
        status=status,
        human_approved=True,
        metadata_json={},
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def add_open_trade(
    db,
    *,
    symbol: str = "AAPL",
    execution_mode: str = "ibkr",
    broker_order_id: str | None = "101",
    metadata: dict | None = None,
) -> Trade:
    trade = Trade(
        symbol=symbol,
        pattern="cup_handle",
        side="long",
        qty=5,
        entry=10.0,
        stop=9.0,
        target=14.0,
        status=TradeStatus.OPEN,
        opened_at=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
        broker_order_id=broker_order_id,
        metadata_json={"execution_mode": execution_mode, **(metadata or {})},
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


class FakeBroker:
    def __init__(
        self,
        *,
        positions: list[dict] | None = None,
        open_orders: list[dict] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._positions = positions or []
        self._open_orders = open_orders or []
        self._error = error

    def positions(self) -> list[dict]:
        if self._error is not None:
            raise self._error
        return self._positions

    def open_orders(self) -> list[dict]:
        if self._error is not None:
            raise self._error
        return self._open_orders


def audit_actions(db) -> list[str]:
    return [row.action for row in db.query(AuditLog).all()]


# ---------------------------------------------------------------------------
# Paper broker: signal -> trade transitions
# ---------------------------------------------------------------------------


def test_paper_broker_opens_trade_and_marks_signal_executed() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)

    trade = PaperBroker().execute_signal(db, signal)

    assert trade.status == TradeStatus.OPEN
    assert signal.status == SignalStatus.EXECUTED
    assert trade.metadata_json["no_ibkr_order"] is True
    assert trade.evidence_type == EvidenceType.SHADOW_NO_ORDER.value
    assert "paper_trade_opened" in audit_actions(db)


@pytest.mark.parametrize(
    "status",
    [
        SignalStatus.WATCHLIST,
        SignalStatus.REJECTED,
        SignalStatus.PENDING_HUMAN_APPROVAL,
        SignalStatus.EXECUTED,
        SignalStatus.EXPIRED,
    ],
)
def test_paper_broker_rejects_non_executable_signal_states(status: SignalStatus) -> None:
    db = session_factory()
    signal = add_signal(db, status=status)

    with pytest.raises(ValueError, match="not executable"):
        PaperBroker().execute_signal(db, signal)

    assert db.query(Trade).count() == 0
    assert signal.status == status


def test_paper_broker_rejects_zero_quantity() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED, qty=0)

    with pytest.raises(ValueError, match="suggested_qty"):
        PaperBroker().execute_signal(db, signal)

    assert db.query(Trade).count() == 0


# ---------------------------------------------------------------------------
# Lab shadow observation lifecycle: OPEN -> CLOSED / pending
# ---------------------------------------------------------------------------


class FakeProvider:
    def __init__(self, frame: pd.DataFrame | None = None, error: Exception | None = None) -> None:
        self._frame = frame
        self._error = error

    def fetch_ohlcv(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        if self._error is not None:
            raise self._error
        assert self._frame is not None
        return self._frame


def make_frame(rows: list[dict], start: datetime) -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [pd.Timestamp(start + timedelta(days=offset)) for offset in range(len(rows))]
    )
    return pd.DataFrame(rows, index=index)


def add_shadow_observation(db, *, symbol: str = "AAPL") -> Trade:
    signal = add_signal(db, status=SignalStatus.EXECUTED, symbol=symbol)
    trade = Trade(
        signal_id=signal.id,
        symbol=symbol,
        pattern="cup_handle",
        side="long",
        qty=5,
        entry=10.0,
        stop=9.0,
        target=14.0,
        status=TradeStatus.OPEN,
        opened_at=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
        evidence_type=EvidenceType.SHADOW_NO_ORDER.value,
        evidence_quality=EvidenceQuality.NORMAL.value,
        metadata_json={
            "execution_mode": "lab_shadow_observation",
            "observation_only": True,
            "no_ibkr_order": True,
            "evidence_type": EvidenceType.SHADOW_NO_ORDER.value,
            "evidence_quality": EvidenceQuality.NORMAL.value,
        },
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def observation_service(provider: FakeProvider) -> LabPaperObservationService:
    return LabPaperObservationService(settings=Settings(), provider=provider)


def test_shadow_observation_transitions_open_to_closed_on_target_hit() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    frame = make_frame(
        [
            {"open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5, "volume": 1000.0},
            {"open": 10.5, "high": 14.5, "low": 10.0, "close": 14.0, "volume": 1000.0},
        ],
        start=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
    )

    result = observation_service(FakeProvider(frame)).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 1
    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == 14.0
    assert trade.r_multiple == pytest.approx(4.0)
    assert trade.metadata_json["exit_reason"] == "target_hit"
    # A shadow close must never masquerade as broker fill evidence.
    assert trade.evidence_type == EvidenceType.SHADOW_NO_ORDER.value
    assert trade.metadata_json["fill_provenance"] == FillProvenance.SHADOW_CLOSE.value
    assert "lab_shadow_observation_closed" in audit_actions(db)


def test_shadow_observation_transitions_open_to_closed_on_stop_hit() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    frame = make_frame(
        [{"open": 10.0, "high": 10.2, "low": 8.5, "close": 8.8, "volume": 1000.0}],
        start=datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc),
    )

    result = observation_service(FakeProvider(frame)).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 1
    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == 9.0
    assert trade.r_multiple == pytest.approx(-1.0)
    assert trade.metadata_json["exit_reason"] == "stop_hit"


def test_shadow_observation_stays_open_without_future_bars() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    # Only bars at/before opened_at: nothing to evaluate yet.
    frame = make_frame(
        [{"open": 10.0, "high": 10.2, "low": 9.8, "close": 10.0, "volume": 1000.0}],
        start=datetime(2026, 5, 28, 15, 0, tzinfo=timezone.utc),
    )

    result = observation_service(FakeProvider(frame)).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 0
    assert trade.status == TradeStatus.OPEN
    assert trade.metadata_json["last_shadow_lifecycle_status"] == "awaiting_future_market_bars"


def test_shadow_observation_stays_open_when_market_data_unavailable() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    provider = FakeProvider(error=RuntimeError("provider down"))

    result = observation_service(provider).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 0
    assert result["data_errors"]
    assert trade.status == TradeStatus.OPEN
    assert trade.metadata_json["market_data_unavailable"] is True


def test_open_observation_is_idempotent_per_signal() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.EXECUTED)
    signal.metadata_json = {"entry_module": "laboratory", "pattern_id": 1}
    db.commit()
    service = observation_service(FakeProvider(pd.DataFrame()))

    class Risk:
        suggested_qty = 5

    first = service.open_observation(db, signal=signal, match={}, risk=Risk())
    second = service.open_observation(db, signal=signal, match={}, risk=Risk())

    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert db.query(Trade).filter(Trade.status == TradeStatus.OPEN).count() == 1


# ---------------------------------------------------------------------------
# Evidence promotion: order -> fill only on real closed executions
# ---------------------------------------------------------------------------


def test_paper_order_promotes_to_paper_fill_only_when_closed_with_real_provenance() -> None:
    metadata = {
        "evidence_type": EvidenceType.IBKR_PAPER_ORDER.value,
        "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
    }

    assert (
        evidence_type_for_metadata(metadata, trade_status=TradeStatus.OPEN)
        == EvidenceType.IBKR_PAPER_ORDER.value
    )
    assert (
        evidence_type_for_metadata(metadata, trade_status=TradeStatus.CANCELLED)
        == EvidenceType.IBKR_PAPER_ORDER.value
    )
    assert (
        evidence_type_for_metadata(metadata, trade_status=TradeStatus.CLOSED)
        == EvidenceType.IBKR_PAPER_FILL.value
    )


def test_paper_order_with_simulated_close_never_becomes_fill() -> None:
    metadata = {
        "evidence_type": EvidenceType.IBKR_PAPER_ORDER.value,
        "fill_provenance": FillProvenance.SIMULATED_CLOSE.value,
    }

    assert (
        evidence_type_for_metadata(metadata, trade_status=TradeStatus.CLOSED)
        == EvidenceType.IBKR_PAPER_ORDER.value
    )


def test_live_order_promotes_to_live_fill_on_closed_statement_import() -> None:
    metadata = {
        "evidence_type": EvidenceType.LIVE_ORDER.value,
        "fill_provenance": FillProvenance.BROKER_STATEMENT_IMPORT.value,
    }

    assert (
        evidence_type_for_metadata(metadata, trade_status=TradeStatus.CLOSED)
        == EvidenceType.LIVE_FILL.value
    )


# ---------------------------------------------------------------------------
# Reconciliation: divergences, kill switch, broker-unreachable
# ---------------------------------------------------------------------------


def reconciliation_service(broker: FakeBroker, **settings_overrides) -> ReconciliationService:
    return ReconciliationService(settings=Settings(**settings_overrides), broker=broker)


def test_reconciliation_clean_state_keeps_kill_switch_off() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL")
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["ok"] is True
    assert result["divergences"] == []
    assert result["kill_switch_activated"] is False
    assert runtime_kill_switch_active(db) is False
    assert "reconciliation_completed" in audit_actions(db)


def test_reconciliation_open_order_counts_as_consistent_state() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL")
    broker = FakeBroker(open_orders=[{"symbol": "AAPL", "order_id": 101}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False


def test_reconciliation_db_trade_missing_at_broker_trips_kill_switch() -> None:
    db = session_factory()
    trade = add_open_trade(db, symbol="AAPL")
    broker = FakeBroker()

    result = reconciliation_service(broker).reconcile(db)

    assert result["kill_switch_activated"] is True
    assert runtime_kill_switch_active(db) is True
    assert result["divergences"] == [
        {
            "kind": "db_open_trade_missing_at_broker",
            "symbol": "AAPL",
            "trade_id": trade.id,
            "broker_order_id": "101",
        }
    ]
    actions = audit_actions(db)
    assert "reconciliation_completed" in actions
    assert "runtime_kill_switch_activated" in actions


def test_reconciliation_broker_position_not_in_db_trips_kill_switch() -> None:
    db = session_factory()
    broker = FakeBroker(positions=[{"symbol": "MSFT", "position": 3.0}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == [
        {"kind": "broker_position_not_in_db", "symbol": "MSFT"}
    ]
    assert result["kill_switch_activated"] is True
    assert runtime_kill_switch_active(db) is True


def test_reconciliation_ignores_zero_quantity_broker_positions() -> None:
    db = session_factory()
    broker = FakeBroker(positions=[{"symbol": "MSFT", "position": 0.0}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False


def test_reconciliation_ignores_non_ibkr_open_trades() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", execution_mode="paper", broker_order_id=None)
    add_open_trade(
        db,
        symbol="MSFT",
        execution_mode="lab_shadow_observation",
        broker_order_id=None,
    )
    broker = FakeBroker()

    result = reconciliation_service(broker).reconcile(db)

    assert result["db_open_ibkr_trades"] == 0
    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False


def test_reconciliation_broker_unreachable_never_trips_kill_switch() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL")
    broker = FakeBroker(error=ConnectionError("gateway down"))

    result = reconciliation_service(broker).reconcile(db)

    assert result["ok"] is False
    assert "broker_unreachable" in result["error"]
    assert result["kill_switch_activated"] is False
    assert runtime_kill_switch_active(db) is False
    actions = audit_actions(db)
    assert "reconciliation_broker_unreachable" in actions
    assert "runtime_kill_switch_activated" not in actions


def test_reconciliation_divergence_respects_disabled_auto_kill_switch() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL")
    broker = FakeBroker()

    result = reconciliation_service(
        broker, reconciliation_auto_kill_switch=False
    ).reconcile(db)

    assert result["divergences"]
    assert result["kill_switch_activated"] is False
    assert runtime_kill_switch_active(db) is False
    assert "reconciliation_completed" in audit_actions(db)


def test_reconciliation_reports_pre_existing_kill_switch() -> None:
    db = session_factory()
    activate_runtime_kill_switch(db, reason="manual", actor="test")
    broker = FakeBroker()

    result = reconciliation_service(broker).reconcile(db)

    assert result["kill_switch_already_active"] is True
    assert result["kill_switch_activated"] is False


# ---------------------------------------------------------------------------
# Kill switch state machine: activation blocks orders, deactivation restores
# ---------------------------------------------------------------------------


def test_active_kill_switch_blocks_ibkr_order_submission() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)
    activate_runtime_kill_switch(db, reason="reconciliation divergence", actor="test")

    with pytest.raises(IBKRSafetyError, match="kill switch"):
        IBKRBroker(settings=Settings()).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.PAPER_APPROVED


def test_kill_switch_activation_is_idempotent_and_audited() -> None:
    db = session_factory()
    activate_runtime_kill_switch(db, reason="first", actor="test")
    activate_runtime_kill_switch(db, reason="second", actor="test")

    assert runtime_kill_switch_active(db) is True
    activations = [
        row
        for row in db.query(AuditLog).all()
        if row.action == "runtime_kill_switch_activated"
    ]
    assert len(activations) == 2
    assert activations[1].details_json["already_active"] is True


def test_kill_switch_deactivation_requires_explicit_actor_and_is_audited() -> None:
    db = session_factory()
    activate_runtime_kill_switch(db, reason="divergence", actor="reconciliation")

    control = deactivate_runtime_kill_switch(db, reason="human investigated", actor="asier")

    assert control is not None
    assert control.enabled is False
    assert runtime_kill_switch_active(db) is False
    assert "runtime_kill_switch_deactivated" in audit_actions(db)
