from __future__ import annotations

import json
from pathlib import Path

from tradeo.modules.lab_foxhunter.gates import (
    LabProbeMetrics,
    LiveAuthorization,
    ResearchLabEvidence,
    foxhunter_to_live_gate,
    lab_to_foxhunter_gate,
    research_to_lab_gate,
    validate_lab_paper_probe_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _valid_research_evidence(**overrides: object) -> ResearchLabEvidence:
    values = {
        "no_lookahead": True,
        "no_leakage": True,
        "product_policy_ok": True,
        "data_quality_ok": True,
        "pattern_documented": True,
        "hypothesis_clear": True,
        "operational_risk_bounded": True,
        "failure_reason_fatal": False,
        "security_ok": True,
        "director_approved": True,
        "logs_available": True,
        "reproducible": True,
        "live_risk": False,
    }
    values.update(overrides)
    return ResearchLabEvidence(**values)


def _valid_lab_metrics(**overrides: object) -> LabProbeMetrics:
    values = {
        "paper_trades_count": 20,
        "success_count": 12,
        "expectancy_net": 0.01,
        "profit_factor": 1.2,
        "max_drawdown": 0.05,
        "max_drawdown_limit": 0.1,
        "avg_slippage_bps": 12.0,
        "slippage_destructive": False,
        "fill_rate": 1.0,
        "rejected_orders": 0,
        "operational_errors": 0,
        "reconciliation_errors": 0,
        "top_symbols_events_concentrated": False,
        "last_n_trades_degraded": False,
        "logs_complete": True,
        "manual_overrides": 0,
        "director_approved": True,
    }
    values.update(overrides)
    return LabProbeMetrics(**values)


def _valid_live_authorization(**overrides: object) -> LiveAuthorization:
    values = {
        "foxhunter_gate_passed": True,
        "risk_review_passed": True,
        "kill_switch_tested": True,
        "live_armed_controlled": True,
        "max_daily_loss_configured": True,
        "max_position_value_configured": True,
        "max_trades_configured": True,
        "paper_live_account_separation": True,
        "human_review_complete": True,
        "explicit_asier_or_director_authorization": True,
    }
    values.update(overrides)
    return LiveAuthorization(**values)


def test_lab_paper_probe_manifest_schema_valid() -> None:
    manifest = json.loads(
        (REPO_ROOT / "research/lab_foxhunter/lab_paper_probe_manifest.example.json").read_text(
            encoding="utf-8"
        )
    )

    decision = validate_lab_paper_probe_manifest(manifest)

    assert decision.allowed is True
    assert decision.blockers == ()


def test_lab_probe_disabled_by_default() -> None:
    manifest = json.loads(
        (REPO_ROOT / "research/lab_foxhunter/lab_paper_probe_manifest.example.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["disabled_by_default"] is True
    assert manifest["execution_enabled"] is False
    assert manifest["live_allowed"] is False


def test_research_to_lab_blocks_lookahead() -> None:
    decision = research_to_lab_gate(_valid_research_evidence(no_lookahead=False))

    assert decision.allowed is False
    assert "lookahead" in decision.blockers


def test_research_to_lab_blocks_live_risk() -> None:
    decision = research_to_lab_gate(_valid_research_evidence(live_risk=True))

    assert decision.allowed is False
    assert "live_risk" in decision.blockers


def test_lab_to_foxhunter_requires_20_trades() -> None:
    decision = lab_to_foxhunter_gate(_valid_lab_metrics(paper_trades_count=19))

    assert decision.allowed is False
    assert "min_paper_trades_20_required" in decision.blockers


def test_lab_to_foxhunter_requires_12_successes() -> None:
    decision = lab_to_foxhunter_gate(_valid_lab_metrics(success_count=11))

    assert decision.allowed is False
    assert "min_successes_12_required" in decision.blockers


def test_lab_to_foxhunter_requires_positive_expectancy() -> None:
    decision = lab_to_foxhunter_gate(_valid_lab_metrics(expectancy_net=0.0))

    assert decision.allowed is False
    assert "positive_net_expectancy_required" in decision.blockers


def test_foxhunter_to_live_requires_explicit_approval() -> None:
    decision = foxhunter_to_live_gate(
        _valid_live_authorization(explicit_asier_or_director_authorization=False)
    )

    assert decision.allowed is False
    assert "explicit_asier_or_director_authorization" in decision.blockers


def test_no_paper_orders_generated_by_gate_check() -> None:
    manifest = json.loads(
        (REPO_ROOT / "research/lab_foxhunter/lab_paper_probe_manifest.example.json").read_text(
            encoding="utf-8"
        )
    )

    decision = validate_lab_paper_probe_manifest(manifest)

    assert decision.allowed is True
    assert decision.no_execution_outputs is True
    assert "paper_order" not in set(manifest["allowed_outputs"])


def test_no_signal_preview_order_outputs() -> None:
    manifest = json.loads(
        (REPO_ROOT / "research/lab_foxhunter/lab_paper_probe_manifest.example.json").read_text(
            encoding="utf-8"
        )
    )

    forbidden = {"signal", "order_preview", "paper_order", "live_order"}

    assert forbidden.isdisjoint(set(manifest["allowed_outputs"]))
    assert manifest["generate_signals"] is False
    assert manifest["generate_previews"] is False
