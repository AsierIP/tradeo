from __future__ import annotations

from tradeo.services.order_outcomes import classify_order_failure


def test_runtime_kill_switch_order_failure_is_safety_block() -> None:
    outcome = classify_order_failure("runtime kill switch is active (see system_controls)")

    assert outcome["reason_code"] == "order_blocked_by_safety"
    assert outcome["retryable"] is False
    assert outcome["next_action"] == "fix_configuration_then_retry"
