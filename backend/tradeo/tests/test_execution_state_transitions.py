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
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternStatus,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.db.session import Base
from tradeo.modules.laboratory.paper_observations import LabPaperObservationService
from tradeo.services import ibkr_broker as ibkr_broker_module
from tradeo.services.evidence import (
    EvidenceQuality,
    EvidenceType,
    FillProvenance,
    evidence_type_for_metadata,
)
from tradeo.services.ibkr_broker import (
    IBKRBroker,
    IBKROperationalError,
    IBKRSafetyError,
    _bracket_acknowledged,
    _operational_bracket_prices,
    _parent_order_acknowledged,
)
from tradeo.services.implementation_shortfall import trade_execution_adjusted_r
from tradeo.modules.fox_hunter.production_manifest import build_production_manifest
from tradeo.services.paper_broker import PaperBroker
from tradeo.services.runtime_status import write_worker_heartbeat
from tradeo.routers.risk import set_kill_switch
from tradeo.schemas import KillSwitchRequest
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


def add_production_pattern(db, *, active_manifest: bool = True) -> DiscoveredPattern:
    pattern = DiscoveredPattern(
        pattern_key="FOX_PATTERN_1",
        name="FOX_PATTERN_1",
        status=DiscoveredPatternStatus.PRODUCTION,
        promotion_status=DiscoveredPatternStatus.PRODUCTION.value,
        validation_passed=True,
        expectancy_r=0.25,
        profit_factor=1.8,
        best_expectancy_r=0.4,
        best_profit_factor=2.0,
    )
    db.add(pattern)
    db.flush()
    if active_manifest:
        manifest = build_production_manifest(
            pattern,
            reviewer="test-director",
            evidence_packet={
                "id": "packet-1",
                "hash": "abc123",
                "gate_scope": "director_production_gate",
                "approved_for_production": True,
                "blockers": [],
                "ibkr_paper_fills": 30,
                "min_paper_fills": 25,
                "effective_paper_fills": 25.0,
                "min_effective_paper_fills": 25.0,
                "unique_fill_symbols": 8,
                "min_fill_symbols": 8,
                "unique_fill_days": 10,
                "min_fill_trading_days": 10,
                "scientific_contracts": {
                    "director_gate_passed": True,
                    "blockers": [],
                    "evidence_packet": {"ref": "packet-1", "hash": "abc123"},
                    "execution_provenance": {
                        "costs_reconciled": True,
                        "slippage_reconciled": True,
                        "fills_reconciled": True,
                    },
                },
            },
        )
        pattern.metrics_json = {"production_manifest": manifest}
    db.commit()
    db.refresh(pattern)
    return pattern


def add_open_trade(
    db,
    *,
    symbol: str = "AAPL",
    execution_mode: str = "ibkr",
    broker_order_id: str | None = "101",
    qty: int = 5,
    side: str = "long",
    metadata: dict | None = None,
) -> Trade:
    trade = Trade(
        symbol=symbol,
        pattern="cup_handle",
        side=side,
        qty=qty,
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
        fills: list[dict] | None = None,
        error: Exception | None = None,
        fill_error: Exception | None = None,
        state_error: Exception | None = None,
    ) -> None:
        self._positions = positions or []
        self._open_orders = open_orders or []
        self._fills = fills or []
        self._fill_error = fill_error or error
        self._state_error = state_error or error

    def fills(self) -> list[dict]:
        if self._fill_error is not None:
            raise self._fill_error
        return self._fills

    def positions(self) -> list[dict]:
        if self._state_error is not None:
            raise self._state_error
        return self._positions

    def open_orders(self) -> list[dict]:
        if self._state_error is not None:
            raise self._state_error
        return self._open_orders


class RepairingFakeBroker(FakeBroker):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.repaired_trade_ids: list[int] = []

    def repair_trade_exit_protection(self, db, trade, *, reason: str):
        self.repaired_trade_ids.append(trade.id)
        return {
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "target_order_id": 201,
            "stop_order_id": 202,
            "target_perm_id": 301,
            "stop_perm_id": 302,
            "oca_group": f"test-{trade.id}",
            "submitted_bracket": {
                "entry": trade.entry,
                "stop": trade.stop,
                "target": trade.target,
            },
        }


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
    assert trade.metadata_json["no_order_reason"] == "legacy_paper_broker_simulated_fill"
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


def test_reconciliation_repairs_missing_paper_exit_protection() -> None:
    db = session_factory()
    trade = add_open_trade(db, symbol="AAPL", broker_order_id="101")
    broker = RepairingFakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}])

    result = reconciliation_service(
        broker,
        ibkr_readonly=False,
        trading_mode="paper",
        reconciliation_auto_repair_paper_exits=True,
    ).reconcile(db)

    assert broker.repaired_trade_ids == [trade.id]
    assert result["divergences"] == []
    assert result["exit_protection_repairs"] == [
        {
            "trade_id": trade.id,
            "symbol": "AAPL",
            "target_order_id": 201,
            "stop_order_id": 202,
            "target_perm_id": 301,
            "stop_perm_id": 302,
            "oca_group": f"test-{trade.id}",
            "submitted_bracket": {
                "entry": 10.0,
                "stop": 9.0,
                "target": 14.0,
            },
        }
    ]
    assert result["warnings"] == [
        {
            "kind": "exit_protection_repaired",
            "symbol": "AAPL",
            "trade_id": trade.id,
            "target_order_id": 201,
            "stop_order_id": 202,
        }
    ]
    assert runtime_kill_switch_active(db) is False


def test_reconciliation_does_not_repair_when_exit_protection_complete() -> None:
    db = session_factory()
    trade = add_open_trade(db, symbol="AAPL", broker_order_id="101")
    broker = RepairingFakeBroker(
        positions=[{"symbol": "AAPL", "position": 5.0}],
        open_orders=[
            {
                "symbol": "AAPL",
                "parent_order_id": 101,
                "action": "SELL",
                "order_type": "LMT",
                "quantity": 5.0,
                "remaining": 5.0,
            },
            {
                "symbol": "AAPL",
                "parent_order_id": 101,
                "action": "SELL",
                "order_type": "STP",
                "quantity": 5.0,
                "remaining": 5.0,
            },
        ],
    )

    result = reconciliation_service(
        broker,
        ibkr_readonly=False,
        trading_mode="paper",
        reconciliation_auto_repair_paper_exits=True,
    ).reconcile(db)

    assert broker.repaired_trade_ids == []
    assert result["exit_protection_repairs"] == []
    assert result["warnings"] == []
    assert trade.status == TradeStatus.OPEN


def test_reconciliation_repairs_unrelated_exit_protection_orders() -> None:
    db = session_factory()
    trade = add_open_trade(db, symbol="AAPL", broker_order_id="101")
    broker = RepairingFakeBroker(
        positions=[{"symbol": "AAPL", "position": 5.0}],
        open_orders=[
            {
                "symbol": "AAPL",
                "parent_order_id": 999,
                "action": "SELL",
                "order_type": "LMT",
                "quantity": 5.0,
                "remaining": 5.0,
            },
            {
                "symbol": "AAPL",
                "parent_order_id": 999,
                "action": "SELL",
                "order_type": "STP",
                "quantity": 5.0,
                "remaining": 5.0,
            },
        ],
    )

    result = reconciliation_service(
        broker,
        ibkr_readonly=False,
        trading_mode="paper",
        reconciliation_auto_repair_paper_exits=True,
    ).reconcile(db)

    assert broker.repaired_trade_ids == [trade.id]
    assert result["exit_protection_repairs"][0]["trade_id"] == trade.id


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


def test_reconciliation_fill_import_failure_warns_without_blocking_state_check() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL")
    broker = FakeBroker(
        positions=[{"symbol": "AAPL", "position": 5.0}],
        fill_error=RuntimeError("execution feed down"),
    )

    result = reconciliation_service(broker).reconcile(db)

    assert result["ok"] is True
    assert result["fill_fetch_error"] == "RuntimeError: execution feed down"
    assert result["broker_fills"] == 0
    assert result["divergences"] == []
    assert result["warnings"] == [
        {"kind": "broker_fills_unavailable", "error": "RuntimeError: execution feed down"}
    ]
    assert result["kill_switch_activated"] is False
    assert runtime_kill_switch_active(db) is False
    actions = audit_actions(db)
    assert "ibkr_fills_unavailable" in actions
    assert "reconciliation_completed" in actions


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
# Reconciliation: explicit qty / order-id / partial-fill checks
# ---------------------------------------------------------------------------


def test_reconciliation_position_larger_than_db_trips_kill_switch() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", qty=5)
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 8.0}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == [
        {
            "kind": "position_qty_mismatch_at_broker",
            "symbol": "AAPL",
            "db_signed_qty": 5.0,
            "broker_signed_qty": 8.0,
        }
    ]
    assert result["kill_switch_activated"] is True
    assert runtime_kill_switch_active(db) is True


def test_reconciliation_position_wrong_side_trips_kill_switch() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", qty=5, side="short")
    broker = FakeBroker(
        positions=[{"symbol": "AAPL", "position": 5.0}],
        open_orders=[{"symbol": "AAPL", "order_id": 101}],
    )

    result = reconciliation_service(broker).reconcile(db)

    assert [d["kind"] for d in result["divergences"]] == [
        "position_qty_mismatch_at_broker"
    ]
    assert result["divergences"][0]["db_signed_qty"] == -5.0
    assert runtime_kill_switch_active(db) is True


def test_reconciliation_smaller_position_with_pending_orders_is_warning_only() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", qty=5)
    broker = FakeBroker(
        positions=[{"symbol": "AAPL", "position": 3.0}],
        open_orders=[
            {
                "symbol": "AAPL",
                "order_id": 101,
                "quantity": 5.0,
                "filled": 3.0,
                "remaining": 2.0,
            }
        ],
    )

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    warning_kinds = sorted(w["kind"] for w in result["warnings"])
    assert warning_kinds == [
        "partial_fill_open_order",
        "position_qty_below_db_pending_orders",
    ]
    assert result["kill_switch_activated"] is False
    assert runtime_kill_switch_active(db) is False
    assert "runtime_kill_switch_activated" not in audit_actions(db)


def test_reconciliation_smaller_position_without_orders_trips_kill_switch() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", qty=5)
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 3.0}])

    result = reconciliation_service(broker).reconcile(db)

    assert [d["kind"] for d in result["divergences"]] == [
        "position_qty_mismatch_at_broker"
    ]
    assert runtime_kill_switch_active(db) is True


def test_reconciliation_sums_multiple_db_trades_per_symbol() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", qty=3, broker_order_id="101")
    add_open_trade(db, symbol="AAPL", qty=2, broker_order_id="102")
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False


def test_reconciliation_unknown_order_id_at_broker_trips_kill_switch() -> None:
    db = session_factory()
    trade = add_open_trade(db, symbol="AAPL", broker_order_id="101")
    broker = FakeBroker(open_orders=[{"symbol": "AAPL", "order_id": 999}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == [
        {
            "kind": "db_order_id_missing_at_broker",
            "symbol": "AAPL",
            "trade_id": trade.id,
            "broker_order_id": "101",
            "broker_open_order_ids": ["999"],
        }
    ]
    assert runtime_kill_switch_active(db) is True


def test_reconciliation_matches_bracket_children_via_parent_order_id() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", broker_order_id="101")
    broker = FakeBroker(
        open_orders=[
            {"symbol": "AAPL", "order_id": 102, "parent_order_id": 101},
            {"symbol": "AAPL", "order_id": 103, "parent_order_id": 101},
        ]
    )

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False


def test_reconciliation_partial_fill_is_audited_warning_never_divergence() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", broker_order_id="101")
    broker = FakeBroker(
        open_orders=[
            {
                "symbol": "AAPL",
                "order_id": 101,
                "quantity": 5.0,
                "filled": 2.0,
                "remaining": 3.0,
            }
        ]
    )

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    assert result["warnings"] == [
        {
            "kind": "partial_fill_open_order",
            "symbol": "AAPL",
            "order_id": 101,
            "filled": 2.0,
            "quantity": 5.0,
            "remaining": 3.0,
        }
    ]
    assert runtime_kill_switch_active(db) is False
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "reconciliation_completed")
        .one()
    )
    assert audit.details_json["warning_count"] == 1
    assert audit.details_json["warnings"][0]["kind"] == "partial_fill_open_order"


def test_reconciliation_ingests_entry_fill_as_paper_fill_evidence() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
            "submitted_at": "2026-06-01T15:00:00+00:00",
            "entry_variant": {"id": "next_bar_limit_retest"},
            "regime": {"regime_key": "market_up|uptrend|normal_vol|liquid|rs_leader"},
        },
    )
    fill = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5.0,
        "price": 10.05,
        "order_id": 101,
        "perm_id": 1001,
        "exec_id": "entry-fill-1",
        "execution_time": "2026-06-01T15:00:12+00:00",
        "commission": 0.35,
        "commission_currency": "USD",
    }
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}], fills=[fill])

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["fills_ingested"] == 1
    assert result["trades_updated_from_fills"] == 1
    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False
    assert trade.status == TradeStatus.OPEN
    assert trade.evidence_type == EvidenceType.IBKR_PAPER_FILL.value
    assert trade.evidence_quality == EvidenceQuality.NORMAL.value
    assert trade.metadata_json["fill_provenance"] == FillProvenance.BROKER_EXECUTION.value
    assert trade.metadata_json["entry_fill_price"] == 10.05
    assert trade.metadata_json["entry_fill_qty"] == 5.0
    assert trade.metadata_json["entry_fill_time"] == "2026-06-01T15:00:12+00:00"
    assert trade.metadata_json["commission_usd"] == 0.35
    assert trade.metadata_json["cost_provenance_reconciled"] is True
    assert trade.metadata_json["slippage_provenance_reconciled"] is True
    assert trade.metadata_json["timestamp_provenance_reconciled"] is True
    assert trade.metadata_json["entry_variant_id"] == "next_bar_limit_retest"
    assert trade.metadata_json["regime_key"] == "market_up|uptrend|normal_vol|liquid|rs_leader"
    assert trade.metadata_json["execution_quality"]["commission_usd"] == 0.35
    assert "ibkr_fills_ingested" in audit_actions(db)


def test_reconciliation_does_not_match_exec_identified_fill_by_symbol_only() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
        },
    )
    fill = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5.0,
        "price": 10.05,
        "exec_id": "unmatched-exec-id",
        "execution_time": "2026-06-01T15:00:12+00:00",
        "commission": 0.35,
        "commission_currency": "USD",
    }
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}], fills=[fill])

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["fills_ingested"] == 0
    assert result["unmatched_fills"] == 1
    assert result["divergences"] == []
    assert "entry_fill_price" not in trade.metadata_json


def test_reconciliation_does_not_match_identified_fill_by_symbol_only() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
        },
    )
    fill = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5.0,
        "price": 10.05,
        "order_id": 999,
        "perm_id": 9999,
        "exec_id": "unrelated-entry-fill",
        "execution_time": "2026-06-01T15:00:12+00:00",
        "commission": 0.35,
        "commission_currency": "USD",
    }
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}], fills=[fill])

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["fills_ingested"] == 0
    assert result["trades_updated_from_fills"] == 0
    assert result["unmatched_fills"] == 1
    assert result["divergences"] == []
    assert "entry_fill_price" not in trade.metadata_json


def test_reconciliation_does_not_cross_match_reused_order_ids_between_symbols() -> None:
    db = session_factory()
    lrn_trade = add_open_trade(
        db,
        symbol="LRN",
        broker_order_id="7",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [7, 8, 9],
            "perm_ids": [7001, 7002, 7003],
            "parent_order_id": 7,
        },
    )
    carg_trade = add_open_trade(
        db,
        symbol="CARG",
        broker_order_id="7",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [7, 10, 11],
            "perm_ids": [7001, 7010, 7011],
            "parent_order_id": 7,
        },
    )
    fill = {
        "symbol": "CARG",
        "side": "BUY",
        "quantity": 5.0,
        "price": 10.05,
        "order_id": 7,
        "perm_id": 7001,
        "exec_id": "carg-entry-fill-7",
        "execution_time": "2026-06-01T15:00:12+00:00",
        "commission": 0.35,
        "commission_currency": "USD",
    }
    broker = FakeBroker(
        positions=[
            {"symbol": "LRN", "position": 5.0},
            {"symbol": "CARG", "position": 5.0},
        ],
        fills=[fill],
    )

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(lrn_trade)
    db.refresh(carg_trade)

    assert result["fills_ingested"] == 1
    assert result["trades_updated_from_fills"] == 1
    assert "entry_fill_price" not in lrn_trade.metadata_json
    assert carg_trade.metadata_json["entry_fill_price"] == 10.05


def test_reconciliation_prunes_existing_fills_from_other_orders() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="LRN",
        side="short",
        qty=4,
        broker_order_id="7",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [7, 8, 9],
            "perm_ids": [7001, 7002, 7003],
            "parent_order_id": 7,
            "ibkr_fills": [
                {
                    "fill_id_hash": "old-fill",
                    "broker_execution_hash": "old-fill",
                    "leg": "entry",
                    "symbol": "LRN",
                    "side": "SELL",
                    "quantity": 1.0,
                    "price": 84.17,
                    "order_id": "4",
                    "perm_id": "4001",
                    "execution_time": "2026-06-01T14:00:00+00:00",
                }
            ],
        },
    )
    fill = {
        "symbol": "LRN",
        "side": "SELL",
        "quantity": 4.0,
        "price": 85.09,
        "order_id": 7,
        "perm_id": 7001,
        "exec_id": "entry-fill-7",
        "execution_time": "2026-06-01T15:00:12+00:00",
        "commission": 0.35,
        "commission_currency": "USD",
    }
    broker = FakeBroker(positions=[{"symbol": "LRN", "position": -4.0}], fills=[fill])

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["fills_ingested"] == 1
    assert result["trades_updated_from_fills"] == 1
    assert result["divergences"] == []
    assert trade.metadata_json["entry_fill_qty"] == 4.0
    assert [record["order_id"] for record in trade.metadata_json["ibkr_fills"]] == ["7"]


def test_reconciliation_fill_without_commission_is_degraded_until_report_arrives() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
        },
    )
    fill = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5.0,
        "price": 10.05,
        "order_id": 101,
        "perm_id": 1001,
        "exec_id": "entry-fill-1",
        "execution_time": "2026-06-01T15:00:12+00:00",
    }
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}], fills=[fill])

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["divergences"] == []
    assert trade.evidence_type == EvidenceType.IBKR_PAPER_FILL.value
    assert trade.evidence_quality == EvidenceQuality.DEGRADED.value
    assert trade.metadata_json["commission_missing"] is True
    assert trade.metadata_json.get("cost_provenance_reconciled") is not True


def test_reconciliation_fill_without_timestamp_is_degraded_until_broker_time_arrives() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
        },
    )
    fill = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5.0,
        "price": 10.05,
        "order_id": 101,
        "perm_id": 1001,
        "exec_id": "entry-fill-1",
        "commission": 0.35,
        "commission_currency": "USD",
    }
    broker = FakeBroker(positions=[{"symbol": "AAPL", "position": 5.0}], fills=[fill])

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["divergences"] == []
    assert trade.evidence_type == EvidenceType.IBKR_PAPER_FILL.value
    assert trade.evidence_quality == EvidenceQuality.DEGRADED.value
    assert trade.metadata_json["entry_fill_price"] == 10.05
    assert trade.metadata_json["entry_fill_time"] is None
    assert trade.metadata_json["broker_timestamp_missing"] is True
    assert trade.metadata_json["broker_timestamp_missing_fill_count"] == 1
    assert trade.metadata_json["timestamp_provenance_reconciled"] is False


def test_reconciliation_ingests_exit_fill_and_closes_without_missing_broker_false_positive() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
        },
    )
    fills = [
        {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 5.0,
            "price": 10.05,
            "order_id": 101,
            "perm_id": 1001,
            "exec_id": "entry-fill-1",
            "execution_time": "2026-06-01T15:00:12+00:00",
            "commission": 0.35,
            "commission_currency": "USD",
        },
        {
            "symbol": "AAPL",
            "side": "SELL",
            "quantity": 5.0,
            "price": 14.0,
            "order_id": 102,
            "perm_id": 1002,
            "exec_id": "exit-fill-1",
            "execution_time": "2026-06-01T16:30:00+00:00",
            "commission": 0.35,
            "commission_currency": "USD",
        },
    ]
    broker = FakeBroker(positions=[], open_orders=[], fills=fills)

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["db_open_ibkr_trades"] == 0
    assert result["trades_closed_from_fills"] == 1
    assert result["divergences"] == []
    assert result["kill_switch_activated"] is False
    assert runtime_kill_switch_active(db) is False
    assert trade.status == TradeStatus.CLOSED
    assert trade.evidence_type == EvidenceType.IBKR_PAPER_FILL.value
    assert trade.evidence_quality == EvidenceQuality.NORMAL.value
    assert trade.exit_price == 14.0
    assert trade.r_multiple == 3.95
    assert trade.metadata_json["exit_reason"] == "target_hit"
    assert trade.metadata_json["exit_fill_time"] == "2026-06-01T16:30:00+00:00"
    assert trade.metadata_json["commission_usd"] == 0.7


def test_reconciliation_closed_partial_entry_uses_executed_quantity_for_pnl_and_r() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        qty=10,
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101, 102, 103],
            "perm_ids": [1001, 1002, 1003],
            "parent_order_id": 101,
        },
    )
    fills = [
        {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 5.0,
            "price": 10.0,
            "order_id": 101,
            "perm_id": 1001,
            "exec_id": "partial-entry-fill-1",
            "execution_time": "2026-06-01T15:00:12+00:00",
            "commission": 0.25,
            "commission_currency": "USD",
        },
        {
            "symbol": "AAPL",
            "side": "SELL",
            "quantity": 5.0,
            "price": 14.0,
            "order_id": 102,
            "perm_id": 1002,
            "exec_id": "partial-exit-fill-1",
            "execution_time": "2026-06-01T16:30:00+00:00",
            "commission": 0.25,
            "commission_currency": "USD",
        },
    ]
    broker = FakeBroker(positions=[], open_orders=[], fills=fills)

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["trades_closed_from_fills"] == 1
    assert trade.status == TradeStatus.CLOSED
    assert trade.pnl_usd == 20.0
    assert trade.r_multiple == 4.0
    assert trade.metadata_json["entry_fill_qty"] == 5.0
    assert trade.metadata_json["exit_fill_qty"] == 5.0
    assert trade.metadata_json["executed_qty_for_pnl"] == 5.0
    assert trade.metadata_json["requested_qty"] == 10.0
    assert trade.metadata_json["partial_fill_close"] is True
    assert trade.metadata_json["commission_usd"] == 0.5
    adjusted = trade_execution_adjusted_r(trade)
    assert adjusted is not None
    assert adjusted["commission_r"] == 0.1
    assert adjusted["net_r"] == 3.9


def test_reconciliation_matches_repaired_exit_fill_metadata() -> None:
    db = session_factory()
    trade = add_open_trade(
        db,
        symbol="AAPL",
        broker_order_id="101",
        metadata={
            "ibkr_mode": "paper",
            "order_ids": [101],
            "perm_ids": [1001],
            "parent_order_id": 101,
            "protective_orders": {
                "target": {"order_id": 501, "perm_id": 5001},
                "stop": {"order_id": 502, "perm_id": 5002},
            },
        },
    )
    fills = [
        {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 5.0,
            "price": 10.0,
            "order_id": 101,
            "perm_id": 1001,
            "exec_id": "entry-fill-101",
            "execution_time": "2026-06-01T15:00:12+00:00",
            "commission": 0.35,
            "commission_currency": "USD",
        },
        {
            "symbol": "AAPL",
            "side": "SELL",
            "quantity": 5.0,
            "price": 14.0,
            "order_id": 501,
            "perm_id": 5001,
            "exec_id": "repaired-target-fill-501",
            "execution_time": "2026-06-01T16:30:00+00:00",
            "commission": 0.35,
            "commission_currency": "USD",
        },
    ]
    broker = FakeBroker(positions=[], open_orders=[], fills=fills)

    result = reconciliation_service(broker).reconcile(db)
    db.refresh(trade)

    assert result["trades_closed_from_fills"] == 1
    assert trade.status == TradeStatus.CLOSED
    assert trade.metadata_json["exit_reason"] == "target_hit"
    assert trade.metadata_json["exit_fill_id_hash"]


def test_reconciliation_trade_without_order_id_skips_order_matching() -> None:
    db = session_factory()
    add_open_trade(db, symbol="AAPL", broker_order_id=None)
    broker = FakeBroker(open_orders=[{"symbol": "AAPL", "order_id": 999}])

    result = reconciliation_service(broker).reconcile(db)

    assert result["divergences"] == []
    assert runtime_kill_switch_active(db) is False


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


def live_order_settings(**overrides) -> Settings:
    values = {
        "trading_mode": "live",
        "live_trading_enabled": True,
        "live_trading_confirmation_value": "I_ACCEPT_LIVE_MARKET_RISK",
        "ibkr_readonly": False,
        "ibkr_account": "DU12345",
        "ibkr_allowed_symbols": "AAPL",
    }
    values.update(overrides)
    return Settings(**values)


def add_live_production_signal(db) -> Signal:
    pattern = add_production_pattern(db, active_manifest=True)
    signal = add_signal(db, status=SignalStatus.LIVE_APPROVED)
    signal.metadata_json = {"entry_module": "fox_hunter", "pattern_id": pattern.id}
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def add_clean_reconciliation_audit(db, *, timestamp: datetime | None = None) -> None:
    db.add(
        AuditLog(
            timestamp=timestamp or datetime.now(timezone.utc),
            actor="reconciliation",
            action="reconciliation_completed",
            entity_type="system",
            entity_id="ibkr",
            details_json={
                "divergence_count": 0,
                "divergences": [],
                "warning_count": 0,
                "warnings": [],
                "exit_protection_error_count": 0,
                "exit_protection_errors": [],
            },
        )
    )
    db.commit()


def test_live_ibkr_submission_rejects_paper_approved_signal_before_connect() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)

    with pytest.raises(IBKRSafetyError, match="live_approved"):
        IBKRBroker(settings=live_order_settings()).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0


def test_live_ibkr_submission_rejects_non_fox_hunter_signal_before_connect() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.LIVE_APPROVED)

    with pytest.raises(IBKRSafetyError, match="Fox Hunter production signal"):
        IBKRBroker(settings=live_order_settings()).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0


def test_live_ibkr_submission_rejects_fox_signal_without_active_production_manifest() -> None:
    db = session_factory()
    pattern = add_production_pattern(db, active_manifest=False)
    signal = add_signal(db, status=SignalStatus.LIVE_APPROVED)
    signal.metadata_json = {"entry_module": "fox_hunter", "pattern_id": pattern.id}
    db.add(signal)
    db.commit()

    with pytest.raises(IBKRSafetyError, match="active production manifest"):
        IBKRBroker(settings=live_order_settings()).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0


@pytest.mark.parametrize(
    ("settings_override", "error"),
    [
        ({"ibkr_account": ""}, "explicit TRADEO_IBKR_ACCOUNT"),
        ({"ibkr_allowed_symbols": ""}, "non-empty TRADEO_IBKR_ALLOWED_SYMBOLS"),
    ],
)
def test_live_ibkr_submission_requires_explicit_account_and_allowlist(
    settings_override: dict,
    error: str,
) -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.LIVE_APPROVED)

    with pytest.raises(IBKRSafetyError, match=error):
        IBKRBroker(settings=live_order_settings(**settings_override)).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0


def test_live_ibkr_submission_requires_central_readiness_before_connect(tmp_path) -> None:
    db = session_factory()
    signal = add_live_production_signal(db)
    settings = live_order_settings(ibkr_port=7496, artifacts_dir=str(tmp_path))
    write_worker_heartbeat(settings)

    with pytest.raises(IBKRSafetyError, match="LiveReadinessGate: missing_clean_reconciliation"):
        IBKRBroker(settings=settings).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.LIVE_APPROVED


def test_live_ibkr_submission_rejects_stale_reconciliation_before_connect(tmp_path) -> None:
    db = session_factory()
    signal = add_live_production_signal(db)
    settings = live_order_settings(ibkr_port=7496, artifacts_dir=str(tmp_path))
    write_worker_heartbeat(settings)
    stale_at = datetime.now(timezone.utc) - timedelta(
        seconds=settings.live_readiness_reconciliation_max_age_seconds + 1
    )
    add_clean_reconciliation_audit(db, timestamp=stale_at)

    with pytest.raises(IBKRSafetyError, match="LiveReadinessGate: stale_reconciliation"):
        IBKRBroker(settings=settings).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.LIVE_APPROVED


def test_live_ibkr_submission_reaches_connect_after_clean_readiness(tmp_path) -> None:
    db = session_factory()
    signal = add_live_production_signal(db)
    settings = live_order_settings(ibkr_port=7496, artifacts_dir=str(tmp_path))
    write_worker_heartbeat(settings)
    add_clean_reconciliation_audit(db)

    class BrokerUnderTest(IBKRBroker):
        def _connect(self):
            raise RuntimeError("connect attempted after live readiness passed")

    with pytest.raises(RuntimeError, match="connect attempted after live readiness passed"):
        BrokerUnderTest(settings=settings).submit_signal_bracket(db, signal)

    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.LIVE_APPROVED


def _open_market_session() -> dict[str, object]:
    return {
        "market": "us_equities",
        "timezone": "America/New_York",
        "regular_session_open": True,
        "state": "regular_open",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "regular_hours": "09:30-16:00",
        "holiday": None,
    }


def _closed_market_session() -> dict[str, object]:
    return {
        **_open_market_session(),
        "regular_session_open": False,
        "state": "market_closed",
    }


def _what_if_state(**overrides) -> SimpleNamespace:
    values = {
        "initMarginBefore": 1000.0,
        "initMarginChange": 100.0,
        "initMarginAfter": 1100.0,
        "maintMarginBefore": 500.0,
        "maintMarginChange": 50.0,
        "maintMarginAfter": 550.0,
        "equityWithLoanBefore": 3000.0,
        "equityWithLoanChange": -100.0,
        "equityWithLoanAfter": 2900.0,
        "commission": 0.05,
        "minCommission": 0.01,
        "maxCommission": 0.05,
        "warningText": "",
        "status": "PreSubmitted",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_ibkr_what_if_order_sets_and_restores_request_timeout() -> None:
    class FakeIB:
        RequestTimeout = 99.0

        def __init__(self) -> None:
            self.seen_timeout = None

        def whatIfOrder(self, contract, order):  # noqa: ANN001, N802
            self.seen_timeout = self.RequestTimeout
            return _what_if_state(status="PreSubmitted")

    fake_ib = FakeIB()
    broker = IBKRBroker(settings=Settings(ibkr_whatif_timeout_seconds=1.25))

    state = broker._what_if_order(fake_ib, SimpleNamespace(), SimpleNamespace())

    assert state.status == "PreSubmitted"
    assert fake_ib.seen_timeout == 1.25
    assert fake_ib.RequestTimeout == 99.0


def test_ibkr_what_if_order_timeout_becomes_operational_error() -> None:
    class FakeIB:
        RequestTimeout = 99.0

        def whatIfOrder(self, contract, order):  # noqa: ANN001, N802
            raise TimeoutError

    fake_ib = FakeIB()
    broker = IBKRBroker(settings=Settings(ibkr_whatif_timeout_seconds=0.5))

    with pytest.raises(IBKROperationalError, match="timed out after 0.5s"):
        broker._what_if_order(fake_ib, SimpleNamespace(), SimpleNamespace())

    assert fake_ib.RequestTimeout == 99.0


def test_ibkr_contract_qualification_uses_request_timeout() -> None:
    class FakeIB:
        RequestTimeout = 99.0

        def __init__(self) -> None:
            self.seen_timeout = None

        def qualifyContracts(self, contract):  # noqa: ANN001, N802
            self.seen_timeout = self.RequestTimeout
            return [contract]

    fake_ib = FakeIB()
    broker = IBKRBroker(settings=Settings(ibkr_whatif_timeout_seconds=2.0))
    contract = SimpleNamespace(symbol="AAPL")

    assert broker._qualify_contracts(fake_ib, contract) == [contract]
    assert fake_ib.seen_timeout == 2.0
    assert fake_ib.RequestTimeout == 99.0


class PreflightFakeIB:
    def __init__(
        self,
        ticker: SimpleNamespace,
        what_if_state: SimpleNamespace | Exception | None = None,
    ) -> None:
        self.ticker = ticker
        self.what_if_state = what_if_state or _what_if_state()
        self.req_mkt_data_calls = 0
        self.what_if_calls = 0
        self.bracket_calls = 0
        self.placed_orders: list[object] = []
        self.cancelled_orders: list[object] = []

    def qualifyContracts(self, contract):
        return [contract]

    def reqMktData(self, contract, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        self.req_mkt_data_calls += 1
        return self.ticker

    def whatIfOrder(self, contract, order):  # noqa: ANN001, N802
        self.what_if_calls += 1
        if isinstance(self.what_if_state, Exception):
            raise self.what_if_state
        return self.what_if_state

    def bracketOrder(
        self,
        *,
        action,
        quantity,
        limitPrice,
        takeProfitPrice,
        stopLossPrice,
    ):
        self.bracket_calls += 1
        return [
            SimpleNamespace(
                orderId=10,
                parentId=0,
                action=action,
                orderType="LMT",
                totalQuantity=quantity,
                lmtPrice=limitPrice,
            ),
            SimpleNamespace(
                orderId=11,
                parentId=10,
                action="SELL",
                orderType="LMT",
                totalQuantity=quantity,
                lmtPrice=takeProfitPrice,
            ),
            SimpleNamespace(
                orderId=12,
                parentId=10,
                action="SELL",
                orderType="STP",
                totalQuantity=quantity,
                auxPrice=stopLossPrice,
            ),
        ]

    def placeOrder(self, contract, order):  # noqa: ANN001
        self.placed_orders.append(order)
        return SimpleNamespace(
            order=order,
            orderStatus=SimpleNamespace(
                permId=20_000 + len(self.placed_orders),
                status="Submitted",
            ),
            log=[],
        )

    def cancelOrder(self, order) -> None:  # noqa: ANN001
        self.cancelled_orders.append(order)

    def sleep(self, seconds: float) -> None:
        return None

    def isConnected(self) -> bool:
        return True

    def disconnect(self) -> None:
        return None


class PaperAccountFakeIB(PreflightFakeIB):
    def __init__(self, *, account: str) -> None:
        super().__init__(
            SimpleNamespace(
                bid=9.99,
                ask=10.01,
                last=10.0,
                bidSize=100,
                askSize=100,
                time=datetime.now(timezone.utc),
            )
        )
        self.account = account

    def managedAccounts(self):
        return [self.account]


class LivePreflightBrokerUnderTest(IBKRBroker):
    def __init__(self, *, fake_ib: PreflightFakeIB, settings: Settings) -> None:
        super().__init__(settings=settings)
        self.fake_ib = fake_ib

    def _connect(self):
        return self.fake_ib

    def _stock_contract(self, symbol: str):
        return SimpleNamespace(
            conId=123,
            symbol=symbol.upper(),
            secType="STK",
            exchange="SMART",
            currency="USD",
        )

    def _build_parent_limit_order(self, signal: Signal):
        return SimpleNamespace(
            action=self._action_for_signal(signal),
            orderType="LMT",
            totalQuantity=int(signal.suggested_qty),
            lmtPrice=float(signal.entry),
            tif="DAY",
            account=self.settings.ibkr_account,
        )


def _live_submit_fixture(tmp_path):
    db = session_factory()
    signal = add_live_production_signal(db)
    settings = live_order_settings(
        ibkr_port=7496,
        artifacts_dir=str(tmp_path),
        ibkr_execution_preflight_quote_timeout_seconds=0.0,
        signal_spread_snapshot_timeout_seconds=0.0,
    )
    write_worker_heartbeat(settings)
    add_clean_reconciliation_audit(db)
    return db, signal, settings


def test_live_execution_preflight_rejects_closed_market_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(
        ibkr_broker_module,
        "market_session_status",
        lambda: _closed_market_session(),
    )

    with pytest.raises(IBKRSafetyError, match="regular US equity session open"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.req_mkt_data_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.LIVE_APPROVED


def test_live_execution_preflight_rejects_missing_bid_ask_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=None,
            ask=None,
            last=10.0,
            bidSize=None,
            askSize=None,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="fresh usable bid/ask quote snapshot"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.req_mkt_data_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.LIVE_APPROVED


def test_live_execution_preflight_rejects_stale_quote_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc) - timedelta(seconds=30),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="stale quote"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.req_mkt_data_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.LIVE_APPROVED


def test_live_execution_preflight_rejects_wide_spread_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.90,
            ask=10.10,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="wide spread"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_wide_spread_cost_r_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    signal.stop = 9.95
    signal.risk_usd = 0.25
    db.add(signal)
    db.commit()
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="wide spread cost R"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_entry_quote_slippage_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=10.02,
            ask=10.04,
            last=10.03,
            bidSize=200,
            askSize=200,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="entry quote slippage pct"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


@pytest.mark.parametrize(
    ("bid_size", "ask_size", "error"),
    [
        (1, 100, "low bid size"),
        (100, 1, "low ask size"),
    ],
)
def test_live_execution_preflight_rejects_low_bid_ask_size_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    bid_size: int,
    ask_size: int,
    error: str,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=bid_size,
            askSize=ask_size,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match=error):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_low_top_of_book_notional_when_mid_is_low(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=4.99,
            ask=5.01,
            last=5.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="low top-of-book notional"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_top_of_book_notional_just_below_threshold(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.98,
            ask=10.00,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="low top-of-book notional"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_whatif_warning_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        ),
        what_if_state=_what_if_state(
            warningText="insufficient margin",
        ),
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="WhatIf preflight warning"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_high_whatif_commission_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        ),
        what_if_state=_what_if_state(
            commission=10.0,
            minCommission=10.0,
            maxCommission=10.0,
        ),
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="commission USD"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


@pytest.mark.parametrize(
    ("what_if_state", "error"),
    [
        (
            _what_if_state(commission=None),
            "missing/invalid commission",
        ),
        (
            _what_if_state(initMarginAfter=None),
            "missing/invalid initMarginAfter",
        ),
    ],
)
def test_live_execution_preflight_rejects_missing_whatif_commission_or_margin_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    what_if_state: SimpleNamespace,
    error: str,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        ),
        what_if_state=what_if_state,
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match=error):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_rejects_whatif_api_error_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        ),
        what_if_state=RuntimeError("whatif unavailable"),
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match="WhatIf preflight failed"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


@pytest.mark.parametrize(
    ("what_if_override", "error"),
    [
        ({"initMarginAfter": None}, "missing/invalid initMarginAfter"),
        ({"maintMarginAfter": "not-a-number"}, "missing/invalid maintMarginAfter"),
        ({"equityWithLoanAfter": 500.0}, "insufficient margin"),
        ({"commission": None}, "missing/invalid commission"),
        ({"commission": 1.7976931348623157e308}, "missing/invalid commission"),
    ],
)
def test_live_execution_preflight_rejects_invalid_whatif_fields_before_order_placement(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    what_if_override: dict[str, object],
    error: str,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=100,
            time=datetime.now(timezone.utc),
        ),
        what_if_state=_what_if_state(**what_if_override),
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    with pytest.raises(IBKRSafetyError, match=error):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.what_if_calls == 1
    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_live_execution_preflight_persists_fresh_quote_snapshot(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, signal, settings = _live_submit_fixture(tmp_path)
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=9.99,
            ask=10.01,
            last=10.0,
            bidSize=100,
            askSize=200,
            time=datetime.now(timezone.utc),
        )
    )
    monkeypatch.setattr(ibkr_broker_module, "market_session_status", _open_market_session)

    trade = LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
        db,
        signal,
    )

    assert fake_ib.req_mkt_data_calls == 1
    assert fake_ib.bracket_calls == 1
    assert len(fake_ib.placed_orders) == 3
    preflight = trade.metadata_json["execution_preflight"]
    assert preflight["market_session"]["regular_session_open"] is True
    assert fake_ib.what_if_calls == 1
    quote = preflight["quote_snapshot"]
    assert quote["data_basis"] == "ibkr_execution_preflight_quote_snapshot"
    assert quote["bid"] == 9.99
    assert quote["ask"] == 10.01
    assert quote["bid_size"] == 100
    assert quote["ask_size"] == 200
    assert quote["spread_abs"] == pytest.approx(0.02)
    assert quote["spread_cost_r"] == pytest.approx(0.02)
    assert quote["top_of_book_notional_usd"] == pytest.approx(1000.0)
    assert quote["quote_age_seconds"] <= quote["max_age_seconds"]
    assert quote["thresholds"]["max_spread_pct"] == settings.ibkr_execution_preflight_max_spread_pct
    assert quote["entry_quote_price"] == pytest.approx(10.01)
    assert quote["entry_quote_slippage_abs"] == pytest.approx(0.01)
    assert quote["entry_quote_slippage_pct"] == pytest.approx(0.001)
    assert quote["entry_quote_slippage_r"] == pytest.approx(0.01)
    assert quote["thresholds"]["max_entry_slippage_pct"] == (
        settings.ibkr_execution_preflight_max_entry_slippage_pct
    )
    what_if = preflight["what_if"]
    assert what_if["data_basis"] == "ibkr_live_parent_order_what_if"
    assert what_if["init_margin_after"] == pytest.approx(1100.0)
    assert what_if["equity_with_loan_after"] == pytest.approx(2900.0)
    assert what_if["commission"] == pytest.approx(0.05)
    assert what_if["commission_r"] == pytest.approx(0.01)
    assert what_if["thresholds"]["max_commission_usd"] == settings.ibkr_execution_preflight_max_commission_usd
    assert trade.metadata_json["execution_observation"]["execution_preflight"] == preflight
    db.refresh(signal)
    assert signal.metadata_json["execution_observation"]["execution_preflight"] == preflight
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "ibkr_bracket_submitted")
        .one()
    )
    assert audit.details_json["execution_preflight"] == preflight
    assert signal.status == SignalStatus.EXECUTED


def test_paper_submit_skips_live_execution_quote_thresholds(tmp_path) -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)
    settings = Settings(
        trading_mode="paper",
        ibkr_readonly=False,
        ibkr_port=7497,
        ibkr_account="DU123456",
        ibkr_allowed_symbols="AAPL",
        artifacts_dir=str(tmp_path),
        ibkr_execution_preflight_max_spread_pct=0.0,
        ibkr_execution_preflight_max_spread_cost_r=0.0,
        ibkr_execution_preflight_max_entry_slippage_pct=0.0,
        ibkr_execution_preflight_max_entry_slippage_r=0.0,
        ibkr_execution_preflight_min_bid_size=999_999.0,
        ibkr_execution_preflight_min_ask_size=999_999.0,
        ibkr_execution_preflight_min_top_of_book_notional_usd=999_999.0,
    )
    fake_ib = PreflightFakeIB(
        SimpleNamespace(
            bid=None,
            ask=None,
            last=None,
            bidSize=None,
            askSize=None,
            time=None,
        )
    )

    trade = LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
        db,
        signal,
    )

    assert fake_ib.req_mkt_data_calls == 0
    assert fake_ib.what_if_calls == 0
    assert fake_ib.bracket_calls == 1
    assert len(fake_ib.placed_orders) == 3
    assert trade.metadata_json["execution_preflight"] is None
    assert signal.status == SignalStatus.EXECUTED


def test_paper_submit_requires_du_account_on_custom_port(tmp_path) -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)
    settings = Settings(
        trading_mode="paper",
        ibkr_readonly=False,
        ibkr_port=14002,
        ibkr_account="U123456",
        artifacts_dir=str(tmp_path),
    )
    fake_ib = PaperAccountFakeIB(account="U123456")

    with pytest.raises(IBKRSafetyError, match="DU paper account"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def test_paper_submit_blocks_configured_blocked_account(tmp_path) -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)
    settings = Settings(
        trading_mode="paper",
        ibkr_readonly=False,
        ibkr_port=14002,
        ibkr_account="DU123456",
        ibkr_blocked_accounts="DU123456",
        artifacts_dir=str(tmp_path),
    )
    fake_ib = PaperAccountFakeIB(account="DU123456")

    with pytest.raises(IBKRSafetyError, match="TRADEO_IBKR_BLOCKED_ACCOUNTS"):
        LivePreflightBrokerUnderTest(fake_ib=fake_ib, settings=settings).submit_signal_bracket(
            db,
            signal,
        )

    assert fake_ib.bracket_calls == 0
    assert fake_ib.placed_orders == []
    assert db.query(Trade).count() == 0


def _fake_ib_trade(order_id: int, perm_id: int | None, status: str = "PendingSubmit"):
    return SimpleNamespace(
        order=SimpleNamespace(orderId=order_id, parentId=0),
        orderStatus=SimpleNamespace(permId=perm_id or 0, status=status),
        log=[],
    )


def test_paper_bracket_accepts_order_ids_while_live_requires_perm_ids() -> None:
    trades = [
        _fake_ib_trade(4, 2002693128, "PreSubmitted"),
        _fake_ib_trade(5, None, "PendingSubmit"),
        _fake_ib_trade(6, None, "PendingSubmit"),
    ]

    assert _bracket_acknowledged(trades, paper_mode=True) is True
    assert _bracket_acknowledged(trades, paper_mode=False) is False

    trades[1].orderStatus.permId = 2002693129
    trades[2].orderStatus.permId = 2002693130
    assert _bracket_acknowledged(trades, paper_mode=True) is True
    assert _bracket_acknowledged(trades, paper_mode=False) is True


def test_paper_bracket_rejects_terminal_child_status() -> None:
    trades = [
        _fake_ib_trade(4, 2002693128, "PreSubmitted"),
        _fake_ib_trade(5, None, "Cancelled"),
        _fake_ib_trade(6, None, "PendingSubmit"),
    ]

    assert _bracket_acknowledged(trades, paper_mode=True) is False


def test_ibkr_submit_rejects_paper_bracket_without_any_perm_ids() -> None:
    db = session_factory()
    signal = add_signal(db, status=SignalStatus.PAPER_APPROVED)

    class FakeIB:
        def __init__(self) -> None:
            self.placed_orders = []
            self.cancelled_orders = []

        def qualifyContracts(self, contract):
            return [contract]

        def bracketOrder(self, *, action, quantity, limitPrice, takeProfitPrice, stopLossPrice):
            return [
                SimpleNamespace(
                    orderId=4,
                    parentId=0,
                    action=action,
                    orderType="LMT",
                    totalQuantity=quantity,
                    lmtPrice=limitPrice,
                ),
                SimpleNamespace(
                    orderId=5,
                    parentId=4,
                    action="SELL",
                    orderType="LMT",
                    totalQuantity=quantity,
                    lmtPrice=takeProfitPrice,
                ),
                SimpleNamespace(
                    orderId=6,
                    parentId=4,
                    action="SELL",
                    orderType="STP",
                    totalQuantity=quantity,
                    auxPrice=stopLossPrice,
                ),
            ]

        def placeOrder(self, contract, order):
            self.placed_orders.append(order)
            return SimpleNamespace(
                order=order,
                orderStatus=SimpleNamespace(permId=0, status="PendingSubmit"),
                log=[],
            )

        def cancelOrder(self, order) -> None:
            self.cancelled_orders.append(order)

        def sleep(self, seconds: float) -> None:
            return None

        def isConnected(self) -> bool:
            return True

        def managedAccounts(self):
            return ["DU123456"]

        def disconnect(self) -> None:
            return None

    fake_ib = FakeIB()

    class BrokerUnderTest(IBKRBroker):
        @property
        def order_timeout(self) -> float:
            return 0.0

        def _connect(self):
            return fake_ib

        def _stock_contract(self, symbol: str):
            return SimpleNamespace(
                conId=123,
                symbol=symbol.upper(),
                secType="STK",
                exchange="SMART",
                currency="USD",
            )

    broker = BrokerUnderTest(settings=Settings(ibkr_readonly=False, trading_mode="paper"))

    with pytest.raises(IBKRSafetyError, match="no broker perm ids"):
        broker.submit_signal_bracket(db, signal)

    db.refresh(signal)
    assert len(fake_ib.placed_orders) == 3
    assert len(fake_ib.cancelled_orders) == 3
    assert db.query(Trade).count() == 0
    assert signal.status == SignalStatus.PAPER_APPROVED


def test_paper_short_bracket_caps_distant_target_for_ibkr_price_bands() -> None:
    signal = SimpleNamespace(side="short", entry=83.54, stop=90.2568, target=49.9561)

    prices = _operational_bracket_prices(signal, paper_mode=True, max_distance_pct=0.20)

    assert prices["entry"] == 83.54
    assert prices["stop"] == 90.2568
    assert prices["target"] == 66.832
    assert prices["requested"]["target"] == 49.9561
    assert prices["adjusted"] is True


def test_live_bracket_keeps_requested_target() -> None:
    signal = SimpleNamespace(side="short", entry=83.54, stop=90.2568, target=49.9561)

    prices = _operational_bracket_prices(signal, paper_mode=False, max_distance_pct=0.20)

    assert prices["target"] == 49.9561
    assert prices["adjusted"] is False


def test_parent_order_acknowledged_requires_order_id_perm_id_and_non_terminal_status() -> None:
    trade = SimpleNamespace(
        order=SimpleNamespace(orderId=4),
        orderStatus=SimpleNamespace(permId=2002693161, status="Submitted"),
    )

    assert _parent_order_acknowledged(trade) is True

    trade.orderStatus.status = "Cancelled"
    assert _parent_order_acknowledged(trade) is False


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


def test_risk_kill_switch_endpoint_updates_runtime_switch_immediately() -> None:
    db = session_factory()

    enabled = set_kill_switch(
        KillSwitchRequest(enabled=True, reason="manual emergency"),
        "admin",
        db,
    )
    assert enabled["runtime_value"] is True
    assert runtime_kill_switch_active(db) is True

    disabled = set_kill_switch(
        KillSwitchRequest(enabled=False, reason="manual clear"),
        "admin",
        db,
    )
    assert disabled["runtime_value"] is False
    assert runtime_kill_switch_active(db) is False


def test_kill_switch_deactivation_requires_explicit_actor_and_is_audited() -> None:
    db = session_factory()
    activate_runtime_kill_switch(db, reason="divergence", actor="reconciliation")

    control = deactivate_runtime_kill_switch(db, reason="human investigated", actor="asier")

    assert control is not None
    assert control.enabled is False
    assert runtime_kill_switch_active(db) is False
    assert "runtime_kill_switch_deactivated" in audit_actions(db)
