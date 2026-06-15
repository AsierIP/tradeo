from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tradeo.db.models import Signal


def classify_order_failure(error: str) -> dict[str, Any]:
    normalized = error.lower()
    if "did not acknowledge every bracket leg" in normalized or "permid" in normalized:
        reason_code = "ibkr_bracket_not_accepted"
        reason = "IBKR did not acknowledge every bracket leg"
        next_action = "retry_order_submission"
        retryable = True
    elif "could not qualify contract" in normalized:
        reason_code = "ibkr_contract_not_qualified"
        reason = "IBKR could not qualify the contract"
        next_action = "review_symbol_then_retry"
        retryable = False
    elif (
        "readonly=true" in normalized
        or "blocks order submission" in normalized
        or "runtime kill switch" in normalized
    ):
        reason_code = "order_blocked_by_safety"
        reason = "Order submission is blocked by safety settings"
        next_action = "fix_configuration_then_retry"
        retryable = False
    elif "human approval is required" in normalized:
        reason_code = "missing_human_approval"
        reason = "Human approval is required before submission"
        next_action = "approve_then_retry"
        retryable = False
    elif "requires stop" in normalized or "notional" in normalized or "suggested_qty is zero" in normalized:
        reason_code = "invalid_order_parameters"
        reason = "Order parameters failed validation"
        next_action = "rebuild_signal"
        retryable = False
    else:
        reason_code = "broker_submission_failed"
        reason = "Broker submission failed"
        next_action = "retry_order_submission"
        retryable = True

    return {
        "status": next_action,
        "reason_code": reason_code,
        "reason": reason,
        "retryable": retryable,
        "next_action": next_action,
        "error": error,
    }


def mark_signal_order_failure(signal: Signal, error: str) -> dict[str, Any]:
    outcome = classify_order_failure(error)
    outcome["updated_at"] = datetime.now(timezone.utc).isoformat()
    metadata = dict(signal.metadata_json or {})
    metadata["execution_outcome"] = outcome
    metadata["last_order_error"] = error
    signal.metadata_json = metadata
    return outcome
