"""Audit §3.1.4: ambiguity with teeth in the entry scanner.

An ambiguous match (two patterns nearly tied on the same window) must clear an
escalated quality bar or abstain, with the abstention recorded as a near-miss
shadow observation (reason: ambiguous_match) so its outcome stays observable.
"""

from __future__ import annotations

from tradeo.db.models import AuditLog, Signal, Trade
from tradeo.modules.shared.entry_scanner import PatternEntryScanner
from tradeo.tests.test_pattern_entry_scanner import (
    FixtureProvider,
    StaticMatcher,
    near_miss_volume_payload,
    scanner,
    session_factory,
)


def ambiguous_match_payload(**overrides):
    payload = near_miss_volume_payload(
        pattern_name="ambiguous_pattern",
        pattern_key="ambiguous_key",
        entry_gate_passed=True,
        ambiguity_ratio=0.97,
        match_ambiguity={
            "ambiguity_ratio": 0.97,
            "ambiguous": True,
            "second_best_pattern_key": "rival_key",
        },
    )
    metrics = dict(payload["metrics"])
    metrics["entry_gate"] = {
        **metrics["entry_gate"],
        "passed": True,
        "volume_ratio": 1.4,
        "volume_confirmed": True,
        "reason": "entry gate passed",
        "rejection_reasons": [],
    }
    payload["metrics"] = metrics
    payload.update(overrides)
    return payload


def _scan(db, provider, match, **settings_overrides):
    cfg = scanner(
        provider,
        entry_gate_enabled=True,
        **settings_overrides,
    ).settings
    return PatternEntryScanner(settings=cfg, matcher=StaticMatcher(provider, [match])).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )


def test_ambiguous_match_below_escalated_bar_abstains_with_shadow() -> None:
    db = session_factory()
    provider = FixtureProvider()
    match = ambiguous_match_payload()

    result = _scan(
        db,
        provider,
        match,
        entry_min_quality_score=0.0,
        entry_ambiguity_quality_margin=10.0,
    )

    assert result["rejected_by_ambiguity"] == 1
    assert result["orders_submitted"] == 0
    assert result["near_miss_shadow_observations_opened"] == 1
    assert result["signals_created"] == 1

    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "entry_match_rejected_by_ambiguity")
        .one()
    )
    gate = audit.details_json["ambiguity_gate"]
    assert gate["passed"] is False
    assert gate["ambiguity_ratio"] == 0.97
    assert gate["second_best_pattern_key"] == "rival_key"

    signal = db.get(Signal, result["near_miss_signal_ids"][0])
    assert signal.metadata_json["near_miss"] is True
    assert signal.metadata_json["near_miss_type"] == "ambiguous_match_shadow"
    assert "ambiguous_match" in signal.metadata_json["near_miss_reasons"]

    observation = db.get(Trade, result["near_miss_trade_ids"][0])
    assert (
        observation.metadata_json["opened_reason"]
        == "lab_near_miss_ambiguous_match_shadow_observation"
    )
    assert observation.metadata_json["no_ibkr_order"] is True


def test_ambiguous_match_clearing_escalated_bar_proceeds() -> None:
    db = session_factory()
    provider = FixtureProvider()
    match = ambiguous_match_payload()

    result = _scan(
        db,
        provider,
        match,
        entry_min_quality_score=0.0,
        entry_ambiguity_quality_margin=0.0,
    )

    assert result["rejected_by_ambiguity"] == 0
    assert result["signals_created"] == 1
    assert result["near_miss_shadow_observations_opened"] == 0
    signal = db.get(Signal, result["signal_ids"][0])
    gate = signal.metadata_json["match"]["ambiguity_gate"]
    assert gate["passed"] is True
    assert gate["escalated"] is True


def test_unambiguous_match_skips_the_gate() -> None:
    db = session_factory()
    provider = FixtureProvider()
    match = ambiguous_match_payload(
        ambiguity_ratio=0.5,
        match_ambiguity={"ambiguity_ratio": 0.5, "ambiguous": False},
    )

    result = _scan(
        db,
        provider,
        match,
        entry_min_quality_score=0.0,
        entry_ambiguity_quality_margin=10.0,
    )

    assert result["rejected_by_ambiguity"] == 0
    assert result["signals_created"] == 1


def test_ambiguity_gate_disabled_by_flag() -> None:
    db = session_factory()
    provider = FixtureProvider()
    match = ambiguous_match_payload()

    result = _scan(
        db,
        provider,
        match,
        entry_min_quality_score=0.0,
        entry_ambiguity_quality_margin=10.0,
        entry_ambiguity_gate_enabled=False,
    )

    assert result["rejected_by_ambiguity"] == 0
    assert result["signals_created"] == 1
