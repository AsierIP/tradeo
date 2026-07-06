from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tradeo.modules.resource_policy.market_session_resource_policy import (
    JobType,
    PriorityLevel,
    ResourceBudget,
    SessionState,
)

RESOURCE_POLICY_ENFORCEMENT_VERSION = "tradeo.resource_policy.enforcement.v1"


@dataclass(frozen=True, slots=True)
class ResourcePolicyDecision:
    allowed: bool
    job_type: str
    owner: str
    priority: str
    deny_reason: str | None
    session_state: str
    budget: ResourceBudget | None = None
    can_submit_orders: bool = False
    policy_version: str = RESOURCE_POLICY_ENFORCEMENT_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "allowed": self.allowed,
            "job_type": self.job_type,
            "owner": self.owner,
            "priority": self.priority,
            "deny_reason": self.deny_reason,
            "session_state": self.session_state,
            "can_submit_orders": self.can_submit_orders,
        }


def assert_job_allowed(
    job_type: str,
    owner: str,
    session_state: str | None = None,
    policy: Any | None = None,
    *,
    now: datetime | None = None,
) -> ResourcePolicyDecision:
    normalized_job = _normalize_job_type(job_type)
    normalized_owner = _normalize_owner(owner)
    normalized_session = _normalize_session_state(session_state)

    if normalized_job == JobType.LIVE:
        return _blocked(
            normalized_job,
            normalized_owner,
            "live jobs are outside Daily resource policy",
            normalized_session,
        )
    if normalized_job == JobType.PAPER_SUBMIT:
        return _blocked(
            normalized_job,
            normalized_owner,
            "paper submit is blocked unless the Lab Paper Probe gate explicitly owns it",
            normalized_session,
        )
    if normalized_session == SessionState.UNKNOWN:
        return _blocked(
            normalized_job,
            normalized_owner,
            "session state unknown; fail closed",
            normalized_session,
        )
    if policy is None or not hasattr(policy, "decide_job"):
        return _blocked(
            normalized_job,
            normalized_owner,
            "resource policy missing; fail closed",
            normalized_session,
        )

    decision = policy.decide_job(normalized_job, now=now)
    budget = getattr(decision, "budget", None)
    effective_state = _normalize_session_state(
        str(getattr(budget, "session_state", normalized_session or SessionState.UNKNOWN))
    )
    if effective_state == SessionState.UNKNOWN:
        return _blocked(
            normalized_job,
            normalized_owner,
            "session state unknown; fail closed",
            effective_state,
            budget=budget,
        )
    if not bool(getattr(decision, "allowed", False)):
        return _blocked(
            normalized_job,
            normalized_owner,
            str(getattr(decision, "reason", "resource policy denied job")),
            effective_state,
            budget=budget,
            priority=str(getattr(decision, "priority", PriorityLevel.BLOCKED)),
        )
    return ResourcePolicyDecision(
        allowed=True,
        job_type=normalized_job,
        owner=normalized_owner,
        priority=str(getattr(decision, "priority", PriorityLevel.ALLOWED)),
        deny_reason=None,
        session_state=effective_state,
        budget=budget,
        can_submit_orders=False,
    )


def _blocked(
    job_type: str,
    owner: str,
    deny_reason: str,
    session_state: str | None,
    *,
    budget: ResourceBudget | None = None,
    priority: str = PriorityLevel.BLOCKED,
) -> ResourcePolicyDecision:
    return ResourcePolicyDecision(
        allowed=False,
        job_type=job_type,
        owner=owner,
        priority=priority,
        deny_reason=deny_reason,
        session_state=str(session_state or getattr(budget, "session_state", SessionState.UNKNOWN)),
        budget=budget,
        can_submit_orders=False,
    )


def _normalize_job_type(job_type: str) -> str:
    return str(job_type or "").strip().lower()


def _normalize_owner(owner: str) -> str:
    return str(owner or "").strip().lower()


def _normalize_session_state(session_state: str | None) -> str | None:
    if session_state is None:
        return None
    return str(session_state).strip().upper() or None
