from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

from tradeo.modules.resource_policy import JobType, PriorityLevel
from tradeo.modules.resource_policy import ResourceBudget as PolicyResourceBudget
from tradeo.modules.resource_policy.enforcement import (
    DENY_POLICY_MISSING,
    DENY_SESSION_UNKNOWN,
    assert_job_allowed,
)

DAILY_WATCHLIST_OWNER = "lab/research/daily_watchlist"
FAST_DAILY_WATCHLIST_ENGINE_ID = "daily_watchlist_fast_v1"
DAILY_WATCHLIST_PRIORITY = 70

DENY_UNKNOWN_ENGINE = "unknown_engine"
DENY_ENGINE_DISABLED = "engine_disabled"
DENY_OWNER_MISMATCH = "owner_mismatch"
DENY_RESOURCE_UNKNOWN = "resource_budget_unknown"
DENY_RESOURCE_EXHAUSTED = "resource_budget_exhausted"

_OWNER_JOB_TYPES = {
    "lab": {JobType.LAB_EXECUTION, JobType.LAB_READINESS, JobType.LAB_PAPER_PROBE},
    "research": {JobType.RESEARCH_HEAVY, JobType.RESEARCH_LIGHT},
    "daily_watchlist": {
        JobType.DAILY_WATCHLIST_PREP,
        JobType.DAILY_WATCHLIST_REEVAL,
        JobType.FAST_ENGINE,
    },
}


@dataclass(frozen=True, slots=True)
class EngineResourceBudget:
    max_symbols: int
    market_data_requests: int
    cpu_seconds: int
    storage_mb: int = 0
    parallel_slots: int = 1

    def __post_init__(self) -> None:
        for name, value in self.as_dict().items():
            if int(value) < 0:
                raise ValueError(f"{name} budget must be non-negative")

    def as_dict(self) -> dict[str, int]:
        return {
            "max_symbols": int(self.max_symbols),
            "market_data_requests": int(self.market_data_requests),
            "cpu_seconds": int(self.cpu_seconds),
            "storage_mb": int(self.storage_mb),
            "parallel_slots": int(self.parallel_slots),
        }

    def fits_within(self, snapshot: SchedulerResourceSnapshot) -> tuple[bool, str | None]:
        available = snapshot.as_dict()
        for name, required in self.as_dict().items():
            if int(available[name]) < 0:
                return False, DENY_RESOURCE_UNKNOWN
            if int(available[name]) < int(required):
                return False, f"{DENY_RESOURCE_EXHAUSTED}:{name}"
        return True, None

    def remaining_after(self, snapshot: SchedulerResourceSnapshot) -> SchedulerResourceSnapshot:
        available = snapshot.as_dict()
        required = self.as_dict()
        return SchedulerResourceSnapshot(
            max_symbols=available["max_symbols"] - required["max_symbols"],
            market_data_requests=available["market_data_requests"]
            - required["market_data_requests"],
            cpu_seconds=available["cpu_seconds"] - required["cpu_seconds"],
            storage_mb=available["storage_mb"] - required["storage_mb"],
            parallel_slots=available["parallel_slots"] - required["parallel_slots"],
        )


@dataclass(frozen=True, slots=True)
class SchedulerResourceSnapshot:
    max_symbols: int
    market_data_requests: int
    cpu_seconds: int
    storage_mb: int = 0
    parallel_slots: int = 1

    def as_dict(self) -> dict[str, int]:
        return {
            "max_symbols": int(self.max_symbols),
            "market_data_requests": int(self.market_data_requests),
            "cpu_seconds": int(self.cpu_seconds),
            "storage_mb": int(self.storage_mb),
            "parallel_slots": int(self.parallel_slots),
        }


@dataclass(frozen=True, slots=True)
class FastChartEngineDescriptor:
    engine_id: str
    owner: str
    scheduler_job_id: str
    resource_budget: EngineResourceBudget
    priority: int
    enabled: bool = True
    lane: str = "daily_watchlist"
    output_state: str = "lab_watchlist"
    implementation: str = "registry_only"
    can_submit_orders: bool = False

    def __post_init__(self) -> None:
        if not self.engine_id.strip():
            raise ValueError("engine_id is required")
        if not self.owner.strip():
            raise ValueError("owner is required")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")
        if self.can_submit_orders:
            raise ValueError("fast chart engines are research/watchlist only")


@dataclass(frozen=True, slots=True)
class EngineJobRequest:
    owner: str
    job_type: str
    heavy: bool = False
    engine_id: str = FAST_DAILY_WATCHLIST_ENGINE_ID


@dataclass(frozen=True, slots=True)
class EngineJobDecision:
    allowed: bool
    owner: str
    job_type: str
    priority: str
    deny_reason: str | None
    budget: PolicyResourceBudget | None
    engine_id: str = FAST_DAILY_WATCHLIST_ENGINE_ID
    can_submit_orders: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "owner": self.owner,
            "job_type": self.job_type,
            "priority": self.priority,
            "deny_reason": self.deny_reason,
            "budget": self.budget.public_status() if self.budget is not None else None,
            "engine_id": self.engine_id,
            "can_submit_orders": self.can_submit_orders,
        }


@dataclass(frozen=True, slots=True)
class EngineScheduleDecision:
    allowed: bool
    engine_id: str
    owner: str
    scheduler_job_id: str | None
    priority: int
    resource_budget: EngineResourceBudget
    resource_remaining: SchedulerResourceSnapshot | None
    deny_reason: str | None
    output_state: str
    resource_policy_priority: str | None = None
    resource_policy_reason: str | None = None
    session_state: str | None = None
    can_submit_orders: bool = False

    def as_scheduler_metadata(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "engine_id": self.engine_id,
            "owner": self.owner,
            "scheduler_job_id": self.scheduler_job_id,
            "priority": self.priority,
            "resource_budget": self.resource_budget.as_dict(),
            "resource_remaining": self.resource_remaining.as_dict()
            if self.resource_remaining is not None
            else None,
            "deny_reason": self.deny_reason,
            "output_state": self.output_state,
            "resource_policy_priority": self.resource_policy_priority,
            "resource_policy_reason": self.resource_policy_reason,
            "session_state": self.session_state,
            "can_submit_orders": self.can_submit_orders,
        }


class FastChartEngineRegistry:
    def __init__(
        self,
        engines: Sequence[FastChartEngineDescriptor] | object | None = None,
        resource_policy: object | None = None,
    ) -> None:
        if resource_policy is None and engines is not None and hasattr(engines, "decide_job"):
            resource_policy = engines
            engines = None
        self.resource_policy = resource_policy
        self._engines: dict[str, FastChartEngineDescriptor] = {}
        engine_specs = engines if isinstance(engines, Sequence) else None
        for engine in engine_specs or (_daily_watchlist_engine(),):
            key = _normalize_engine_id(engine.engine_id)
            if key in self._engines:
                raise ValueError(f"duplicate fast chart engine: {engine.engine_id}")
            self._engines[key] = engine

    def get(self, engine_id: str) -> FastChartEngineDescriptor | None:
        return self._engines.get(_normalize_engine_id(engine_id))

    def all(self) -> tuple[FastChartEngineDescriptor, ...]:
        return tuple(
            sorted(self._engines.values(), key=lambda item: (-item.priority, item.engine_id))
        )

    def plan(
        self,
        engine_id: str,
        *,
        resources: SchedulerResourceSnapshot | Mapping[str, int] | None,
        owner: str = DAILY_WATCHLIST_OWNER,
        now: datetime | None = None,
    ) -> EngineScheduleDecision:
        if _normalize_engine_id(engine_id) == FAST_DAILY_WATCHLIST_ENGINE_ID:
            return plan_daily_watchlist_scheduler_run(
                resources=resources,
                owner=owner,
                registry=self,
                resource_policy=self.resource_policy,
                now=now,
            )
        return plan_scheduler_run(
            engine_id,
            resources=resources,
            owner=owner,
            registry=self,
        )

    def request_engine(
        self,
        request: EngineJobRequest,
        *,
        now: datetime | None = None,
    ) -> EngineJobDecision:
        if self.get(request.engine_id) is None:
            return _job_denied(request, DENY_UNKNOWN_ENGINE, priority=PriorityLevel.BLOCKED)
        if self.resource_policy is None or not hasattr(self.resource_policy, "decide_job"):
            return _job_denied(request, "resource_policy_missing", priority=PriorityLevel.BLOCKED)

        owner = _normalize_owner(request.owner)
        job_type = _policy_job_type(request)
        if owner not in _OWNER_JOB_TYPES or job_type not in _OWNER_JOB_TYPES[owner]:
            return _job_denied(request, DENY_OWNER_MISMATCH, priority=PriorityLevel.BLOCKED)

        policy_decision = assert_job_allowed(
            job_type,
            owner,
            policy=self.resource_policy,
            now=now,
        )
        if policy_decision.session_state == "UNKNOWN":
            return EngineJobDecision(
                allowed=False,
                owner=owner,
                job_type=job_type,
                priority=PriorityLevel.BLOCKED,
                deny_reason=DENY_SESSION_UNKNOWN,
                budget=policy_decision.budget,
                engine_id=request.engine_id,
                can_submit_orders=False,
            )

        return EngineJobDecision(
            allowed=bool(policy_decision.allowed),
            owner=owner,
            job_type=job_type,
            priority=str(policy_decision.priority),
            deny_reason=None if policy_decision.allowed else str(policy_decision.deny_reason),
            budget=policy_decision.budget,
            engine_id=request.engine_id,
            can_submit_orders=False,
        )

    def arbitrate(
        self,
        requests: Sequence[EngineJobRequest],
        *,
        now: datetime | None = None,
    ) -> tuple[EngineJobDecision, ...]:
        return tuple(self.request_engine(request, now=now) for request in requests)


def default_engine_registry() -> FastChartEngineRegistry:
    return FastChartEngineRegistry()


def plan_scheduler_run(
    engine_id: str,
    *,
    resources: SchedulerResourceSnapshot | Mapping[str, int] | None,
    owner: str = DAILY_WATCHLIST_OWNER,
    registry: FastChartEngineRegistry | None = None,
) -> EngineScheduleDecision:
    engine_key = _normalize_engine_id(engine_id)
    active_registry = registry or default_engine_registry()
    descriptor = active_registry.get(engine_key)
    if descriptor is None:
        return _deny(
            engine_id=engine_id,
            owner=owner,
            deny_reason=DENY_UNKNOWN_ENGINE,
            resources=resources,
        )
    if not descriptor.enabled:
        return _deny_descriptor(
            descriptor,
            owner=owner,
            resources=resources,
            deny_reason=DENY_ENGINE_DISABLED,
        )
    if owner != descriptor.owner:
        return _deny_descriptor(
            descriptor,
            owner=owner,
            resources=resources,
            deny_reason=DENY_OWNER_MISMATCH,
        )

    snapshot = _coerce_resources(resources)
    if snapshot is None:
        return _deny_descriptor(
            descriptor,
            owner=owner,
            resources=resources,
            deny_reason=DENY_RESOURCE_UNKNOWN,
        )

    fits, reason = descriptor.resource_budget.fits_within(snapshot)
    if not fits:
        return _deny_descriptor(descriptor, owner=owner, resources=snapshot, deny_reason=reason)

    return EngineScheduleDecision(
        allowed=True,
        engine_id=descriptor.engine_id,
        owner=descriptor.owner,
        scheduler_job_id=descriptor.scheduler_job_id,
        priority=descriptor.priority,
        resource_budget=descriptor.resource_budget,
        resource_remaining=descriptor.resource_budget.remaining_after(snapshot),
        deny_reason=None,
        output_state=descriptor.output_state,
        can_submit_orders=False,
    )


def plan_daily_watchlist_scheduler_run(
    *,
    resources: SchedulerResourceSnapshot | Mapping[str, int] | None = None,
    owner: str = DAILY_WATCHLIST_OWNER,
    registry: FastChartEngineRegistry | None = None,
    resource_policy: object | None = None,
    now: datetime | None = None,
) -> EngineScheduleDecision:
    active_registry = registry or default_engine_registry()
    policy_decision = _decide_daily_watchlist_job(resource_policy, now)
    active_resources = resources
    if active_resources is None and policy_decision is not None:
        active_resources = _snapshot_from_policy_budget(policy_decision.budget)

    decision = plan_scheduler_run(
        FAST_DAILY_WATCHLIST_ENGINE_ID,
        resources=active_resources,
        owner=owner,
        registry=active_registry,
    )
    if policy_decision is None:
        descriptor = active_registry.get(FAST_DAILY_WATCHLIST_ENGINE_ID)
        if descriptor is None:
            return decision
        return _deny_descriptor(
            descriptor,
            owner=owner,
            resources=resources,
            deny_reason=DENY_POLICY_MISSING,
            resource_policy_priority=PriorityLevel.BLOCKED,
            resource_policy_reason=DENY_POLICY_MISSING,
            session_state="UNKNOWN",
        )
    if not bool(policy_decision.allowed):
        descriptor = active_registry.get(FAST_DAILY_WATCHLIST_ENGINE_ID)
        if descriptor is None:
            return decision
        return _deny_descriptor(
            descriptor,
            owner=owner,
            resources=active_resources,
            deny_reason=f"resource_policy:{policy_decision.deny_reason}",
            resource_policy_priority=policy_decision.priority,
            resource_policy_reason=policy_decision.deny_reason,
            session_state=policy_decision.session_state,
        )
    return _with_resource_policy(decision, policy_decision)


def _daily_watchlist_engine() -> FastChartEngineDescriptor:
    return FastChartEngineDescriptor(
        engine_id=FAST_DAILY_WATCHLIST_ENGINE_ID,
        owner=DAILY_WATCHLIST_OWNER,
        scheduler_job_id="daily_watchlist_fast_engine",
        priority=DAILY_WATCHLIST_PRIORITY,
        resource_budget=EngineResourceBudget(
            max_symbols=120,
            market_data_requests=10,
            cpu_seconds=30,
            storage_mb=16,
            parallel_slots=1,
        ),
    )


def _deny(
    *,
    engine_id: str,
    owner: str,
    deny_reason: str | None,
    resources: SchedulerResourceSnapshot | Mapping[str, int] | None,
) -> EngineScheduleDecision:
    return EngineScheduleDecision(
        allowed=False,
        engine_id=engine_id,
        owner=owner,
        scheduler_job_id=None,
        priority=0,
        resource_budget=EngineResourceBudget(
            max_symbols=0,
            market_data_requests=0,
            cpu_seconds=0,
            parallel_slots=0,
        ),
        resource_remaining=_coerce_resources(resources),
        deny_reason=deny_reason,
        output_state="UNKNOWN",
        can_submit_orders=False,
    )


def _deny_descriptor(
    descriptor: FastChartEngineDescriptor,
    *,
    owner: str,
    resources: SchedulerResourceSnapshot | Mapping[str, int] | None,
    deny_reason: str | None,
    resource_policy_priority: str | None = None,
    resource_policy_reason: str | None = None,
    session_state: str | None = None,
) -> EngineScheduleDecision:
    return EngineScheduleDecision(
        allowed=False,
        engine_id=descriptor.engine_id,
        owner=owner,
        scheduler_job_id=descriptor.scheduler_job_id,
        priority=descriptor.priority,
        resource_budget=descriptor.resource_budget,
        resource_remaining=_coerce_resources(resources),
        deny_reason=deny_reason,
        output_state=descriptor.output_state,
        resource_policy_priority=resource_policy_priority,
        resource_policy_reason=resource_policy_reason,
        session_state=session_state,
        can_submit_orders=False,
    )


def _coerce_resources(
    resources: SchedulerResourceSnapshot | Mapping[str, int] | None,
) -> SchedulerResourceSnapshot | None:
    if resources is None:
        return None
    if isinstance(resources, SchedulerResourceSnapshot):
        return resources
    try:
        return SchedulerResourceSnapshot(
            max_symbols=int(resources["max_symbols"]),
            market_data_requests=int(resources["market_data_requests"]),
            cpu_seconds=int(resources["cpu_seconds"]),
            storage_mb=int(resources.get("storage_mb", 0)),
            parallel_slots=int(resources.get("parallel_slots", 1)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _decide_daily_watchlist_job(resource_policy: object | None, now: datetime | None) -> object | None:
    if resource_policy is None:
        return None
    if not hasattr(resource_policy, "decide_job"):
        return None
    return assert_job_allowed(
        JobType.DAILY_WATCHLIST_REEVAL,
        "daily_watchlist",
        policy=resource_policy,
        now=now,
    )


def _snapshot_from_policy_budget(budget: PolicyResourceBudget) -> SchedulerResourceSnapshot:
    data = budget.to_dict()
    return SchedulerResourceSnapshot(
        max_symbols=max(0, int(data["max_symbols_research_cycle"])),
        market_data_requests=0 if data["market_data_budget"] == "blocked" else 10,
        cpu_seconds=max(0, int(data["cpu_slots_research"]) * 30),
        storage_mb=0 if data["cache_write_budget"] == "blocked" else 16,
        parallel_slots=max(0, int(data["max_process_pool_workers_research"])),
    )


def _with_resource_policy(
    decision: EngineScheduleDecision,
    policy_decision: object,
) -> EngineScheduleDecision:
    return EngineScheduleDecision(
        allowed=decision.allowed,
        engine_id=decision.engine_id,
        owner=decision.owner,
        scheduler_job_id=decision.scheduler_job_id,
        priority=decision.priority,
        resource_budget=decision.resource_budget,
        resource_remaining=decision.resource_remaining,
        deny_reason=decision.deny_reason,
        output_state=decision.output_state,
        resource_policy_priority=policy_decision.priority,
        resource_policy_reason=policy_decision.deny_reason,
        session_state=policy_decision.session_state,
        can_submit_orders=False,
    )


def _job_denied(
    request: EngineJobRequest,
    deny_reason: str,
    *,
    priority: str,
) -> EngineJobDecision:
    return EngineJobDecision(
        allowed=False,
        owner=_normalize_owner(request.owner),
        job_type=str(request.job_type).strip().lower(),
        priority=priority,
        deny_reason=deny_reason,
        budget=None,
        engine_id=request.engine_id,
        can_submit_orders=False,
    )


def _policy_job_type(request: EngineJobRequest) -> str:
    job_type = str(request.job_type).strip().lower()
    if request.heavy and job_type == JobType.RESEARCH_LIGHT:
        return JobType.RESEARCH_HEAVY
    if job_type == JobType.FAST_ENGINE:
        return JobType.DAILY_WATCHLIST_REEVAL
    return job_type


def _normalize_owner(owner: str) -> str:
    return str(owner or "").strip().lower()


def _normalize_engine_id(engine_id: str) -> str:
    return str(engine_id or "").strip().lower()
