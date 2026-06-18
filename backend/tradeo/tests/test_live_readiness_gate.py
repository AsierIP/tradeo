from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
)
from tradeo.db.session import Base
from tradeo.modules.fox_hunter.production_manifest import build_production_manifest
from tradeo.services.ibkr_broker import IBKRBroker, IBKRSafetyError
from tradeo.services.live_readiness_gate import LiveReadinessGate
from tradeo.services.runtime_status import write_worker_heartbeat
from tradeo.services.system_controls import activate_runtime_kill_switch


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def _live_settings(tmp_path, **overrides) -> Settings:
    defaults = {
        "artifacts_dir": str(tmp_path),
        "trading_mode": "live",
        "live_trading_enabled": True,
        "live_trading_confirmation_value": "I_ACCEPT_LIVE_MARKET_RISK",
        "fox_hunter_auto_submit_live_orders": True,
        "ibkr_readonly": False,
        "ibkr_port": 7496,
        "ibkr_account": "DU123456",
        "ibkr_allowed_symbols": "AAPL,MSFT",
        "live_readiness_worker_max_age_seconds": 120,
        "live_readiness_reconciliation_max_age_seconds": 3600,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _add_production_pattern(db) -> DiscoveredPattern:
    pattern = DiscoveredPattern(
        pattern_key="prod-pattern-1",
        name="prod-pattern-1",
        status=DiscoveredPatternStatus.PRODUCTION,
        promotion_status=DiscoveredPatternStatus.PRODUCTION.value,
        validation_passed=True,
        expectancy_r=0.35,
        profit_factor=2.1,
        best_expectancy_r=0.35,
        best_profit_factor=2.1,
    )
    db.add(pattern)
    db.flush()
    pattern.metrics_json = {
        "production_manifest": build_production_manifest(
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
    }
    db.commit()
    db.refresh(pattern)
    return pattern


def _add_clean_reconciliation(db, *, at: datetime | None = None) -> None:
    db.add(
        AuditLog(
            timestamp=at or datetime.now(timezone.utc),
            actor="reconciliation",
            action="reconciliation_completed",
            entity_type="system",
            entity_id="ibkr",
            details_json={
                "divergence_count": 0,
                "warning_count": 0,
                "exit_protection_error_count": 0,
            },
        )
    )
    db.commit()


def _add_broker_unreachable_reconciliation(db, *, at: datetime) -> None:
    db.add(
        AuditLog(
            timestamp=at,
            actor="reconciliation",
            action="reconciliation_broker_unreachable",
            entity_type="system",
            entity_id="ibkr",
            details_json={"error": "broker_unreachable: timeout"},
        )
    )
    db.commit()


def test_live_readiness_gate_allows_only_when_all_hard_gates_pass(tmp_path) -> None:
    db = _session()
    settings = _live_settings(tmp_path)
    write_worker_heartbeat(settings)
    _add_clean_reconciliation(db)
    _add_production_pattern(db)

    status = LiveReadinessGate(settings).evaluate(db)

    assert status["orders_allowed"] is True
    assert status["primary_block_reason"] is None
    assert status["eligible_production_manifests"] == 1
    assert all(check["ok"] for check in status["checks"])


def test_live_readiness_gate_fails_closed_without_recent_clean_reconciliation(tmp_path) -> None:
    db = _session()
    settings = _live_settings(tmp_path)
    write_worker_heartbeat(settings)
    _add_production_pattern(db)

    missing = LiveReadinessGate(settings).evaluate(db)
    assert missing["orders_allowed"] is False
    assert "missing_clean_reconciliation" in missing["block_reasons"]

    _add_clean_reconciliation(db, at=datetime.now(timezone.utc) - timedelta(hours=3))
    stale = LiveReadinessGate(settings).evaluate(db)
    assert stale["orders_allowed"] is False
    assert "stale_reconciliation" in stale["block_reasons"]


def test_live_readiness_gate_blocks_runtime_kill_and_latest_unreachable(tmp_path) -> None:
    db = _session()
    settings = _live_settings(tmp_path)
    now = datetime.now(timezone.utc)
    write_worker_heartbeat(settings)
    _add_production_pattern(db)
    _add_clean_reconciliation(db, at=now - timedelta(minutes=1))
    _add_broker_unreachable_reconciliation(db, at=now)
    activate_runtime_kill_switch(db, reason="manual halt", actor="pytest")

    status = LiveReadinessGate(settings).evaluate(db, now=now)

    assert status["orders_allowed"] is False
    assert "runtime_kill_switch_enabled" in status["block_reasons"]
    assert "reconciliation_broker_unreachable" in status["block_reasons"]
    assert {"code": "runtime_kill_switch_enabled", "check": "runtime_kill_switch"} in status[
        "blockers"
    ]


def test_live_broker_submit_validation_uses_live_readiness_gate(tmp_path) -> None:
    db = _session()
    settings = _live_settings(tmp_path)
    write_worker_heartbeat(settings)
    pattern = _add_production_pattern(db)
    signal = Signal(
        symbol="AAPL",
        pattern=pattern.name,
        side="long",
        entry=100.0,
        stop=99.0,
        target=104.0,
        reward_risk=4.0,
        confidence=0.9,
        composite_score=0.9,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version="fox_hunter",
        status=SignalStatus.LIVE_APPROVED,
        human_approved=True,
        metadata_json={"entry_module": "fox_hunter", "pattern_id": pattern.id},
    )
    db.add(signal)
    db.commit()

    with pytest.raises(IBKRSafetyError, match="LiveReadinessGate: missing_clean_reconciliation"):
        IBKRBroker(settings=settings)._validate_live_production_signal(db, signal)
