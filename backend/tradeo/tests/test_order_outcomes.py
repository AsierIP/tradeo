from __future__ import annotations

from tradeo.services.order_outcomes import classify_order_failure


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
