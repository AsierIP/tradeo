from __future__ import annotations

from tradeo.db.models import Signal, SignalStatus
from tradeo.services.order_outcomes import (
    classify_order_failure,
    mark_signal_order_failure,
    mark_signal_order_submitted,
)


def test_runtime_kill_switch_order_failure_is_safety_block() -> None:
    outcome = classify_order_failure("runtime kill switch is active (see system_controls)")

    assert outcome["reason_code"] == "order_blocked_by_safety"
    assert outcome["retryable"] is False
    assert outcome["next_action"] == "fix_configuration_then_retry"


def test_static_safety_order_failures_are_not_retryable_broker_errors() -> None:
    errors = [
        "kill switch is enabled",
        "live IBKR execution requires live_armed=true",
        "short orders are disabled by TRADEO_ALLOW_SHORTS",
        "XYZ is not in TRADEO_IBKR_ALLOWED_SYMBOLS",
    ]

    for error in errors:
        outcome = classify_order_failure(error)
        assert outcome["reason_code"] == "order_blocked_by_safety"
        assert outcome["retryable"] is False
        assert outcome["next_action"] == "fix_configuration_then_retry"


def test_final_order_failure_rejects_executable_signal() -> None:
    signal = Signal(
        symbol="LABX",
        pattern="pattern",
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.8,
        composite_score=0.8,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version="laboratory_pattern_1",
        status=SignalStatus.PAPER_APPROVED,
        metadata_json={},
    )

    outcome = mark_signal_order_failure(signal, "readonly=true blocks order submission")

    assert outcome["reason_code"] == "order_blocked_by_safety"
    assert signal.status == SignalStatus.REJECTED
    assert signal.metadata_json["execution_outcome"]["retryable"] is False


def test_successful_order_submission_clears_previous_failure() -> None:
    signal = Signal(
        symbol="LABX",
        pattern="pattern",
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.8,
        composite_score=0.8,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version="daily_pattern_1",
        status=SignalStatus.PAPER_APPROVED,
        metadata_json={
            "last_order_error": "old broker error",
            "execution_outcome": {
                "status": "retry_order_submission",
                "reason_code": "broker_submission_failed",
                "retryable": True,
            },
        },
    )

    outcome = mark_signal_order_submitted(signal, broker_order_id="4", order_ids=[4, 5, 6])

    assert signal.status == SignalStatus.EXECUTED
    assert outcome["status"] == "order_submitted"
    assert outcome["broker_order_id"] == "4"
    assert signal.metadata_json["execution_outcome"]["retryable"] is False
    assert signal.metadata_json["execution_outcome"]["reason_code"] == "ibkr_order_submitted_waiting_fill"
    assert "last_order_error" not in signal.metadata_json
