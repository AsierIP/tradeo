from __future__ import annotations

from tradeo.modules.lab_foxhunter.gates import (
    validate_foxhunter_to_live_gate,
    validate_lab_to_foxhunter_gate,
    validate_manifest,
    validate_research_to_lab_gate,
)


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "probe_id": "LAB-GAP-REV-001",
        "strategy_source_id": "GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL",
        "status": "proposed_lab_paper_probe",
        "rationale": "measure open slippage and fill realism",
        "max_initial_paper_trades": 20,
        "success_threshold": 12,
        "disabled_by_default": True,
        "net_expectancy_required": True,
        "direction_approved": True,
    }
    base.update(overrides)
    return base


def _metrics(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "paper_trades_count": 20,
        "success_count": 12,
        "expectancy_net": 0.04,
        "profit_factor": 1.2,
        "max_drawdown_pct": 4.0,
        "max_allowed_drawdown_pct": 10.0,
        "operational_error_count": 0,
        "reconciliation_errors": 0,
        "symbol_or_event_concentration": False,
        "manual_overrides": False,
        "logs_complete": True,
        "direction_approved": True,
    }
    base.update(overrides)
    return base


def test_lab_paper_probe_manifest_schema_valid() -> None:
    decision = validate_manifest(_manifest())

    assert decision.passed
    assert not decision.orders_allowed
    assert not decision.paper_orders_generated
    assert not decision.live_orders_generated


def test_lab_probe_disabled_by_default() -> None:
    decision = validate_manifest(_manifest(disabled_by_default=False))

    assert not decision.passed
    assert "lab_probe_must_be_disabled_by_default" in decision.blockers


def test_research_to_lab_blocks_lookahead() -> None:
    decision = validate_research_to_lab_gate(_manifest(lookahead_free=False))

    assert not decision.passed
    assert "lookahead_free" in decision.blockers


def test_research_to_lab_blocks_live_risk() -> None:
    decision = validate_research_to_lab_gate(_manifest(live_risk=True))

    assert not decision.passed
    assert "live_risk" in decision.blockers


def test_lab_to_foxhunter_requires_20_trades() -> None:
    decision = validate_lab_to_foxhunter_gate(_metrics(paper_trades_count=19))

    assert not decision.passed
    assert "min_paper_trades_20_required" in decision.blockers


def test_lab_to_foxhunter_requires_12_successes() -> None:
    decision = validate_lab_to_foxhunter_gate(_metrics(success_count=11))

    assert not decision.passed
    assert "min_successes_12_required" in decision.blockers


def test_lab_to_foxhunter_requires_positive_expectancy() -> None:
    decision = validate_lab_to_foxhunter_gate(_metrics(expectancy_net=0.0))

    assert not decision.passed
    assert "positive_expectancy_required" in decision.blockers


def test_foxhunter_to_live_requires_explicit_approval() -> None:
    decision = validate_foxhunter_to_live_gate(
        {
            "foxhunter_review_passed": True,
            "risk_review_passed": True,
            "kill_switch_tested": True,
            "max_daily_loss_defined": True,
            "max_position_value_defined": True,
            "max_trades_defined": True,
            "paper_live_account_separation": True,
            "human_review_complete": True,
        }
    )

    assert not decision.passed
    assert "explicit_asier_authorization" in decision.blockers
    assert "explicit_direction_authorization" in decision.blockers


def test_no_paper_orders_generated_by_gate_check() -> None:
    decision = validate_research_to_lab_gate(_manifest())

    assert decision.passed
    assert not decision.orders_allowed
    assert not decision.paper_orders_generated


def test_no_signal_preview_order_outputs() -> None:
    decision = validate_lab_to_foxhunter_gate(_metrics())

    assert decision.passed
    assert not decision.signals_generated
    assert not decision.previews_generated
    assert not decision.paper_orders_generated
    assert not decision.live_orders_generated
