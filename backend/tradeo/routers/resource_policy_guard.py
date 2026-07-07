from __future__ import annotations

from fastapi import HTTPException

from tradeo.core.config import get_settings
from tradeo.modules.resource_policy.enforcement import (
    blocked_job_status,
    decide_with_market_session_policy,
)


def assert_route_job_allowed(job_type: str, owner: str) -> None:
    decision = decide_with_market_session_policy(job_type, owner, settings=get_settings())
    if decision.allowed:
        return
    blocked = blocked_job_status(decision)
    raise HTTPException(
        status_code=409,
        detail={
            "decision": "blocked_resource_policy",
            "reason": decision.deny_reason,
            "resource_policy": decision.to_dict(),
            "research_result": blocked,
            "can_submit_orders": False,
        },
    )
