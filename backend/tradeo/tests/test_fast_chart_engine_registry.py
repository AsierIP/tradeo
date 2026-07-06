from __future__ import annotations

from tradeo.core.config import Settings
from tradeo.modules.fast_chart_analysis.engine_registry import (
    DENY_UNKNOWN_ENGINE,
    EngineJobRequest,
    FastChartEngineRegistry,
    plan_daily_watchlist_scheduler_run,
)
from tradeo.modules.resource_policy.market_session_resource_policy import MarketSessionResourcePolicy, SessionState


def _registry(tmp_path, state: str) -> FastChartEngineRegistry:
    return FastChartEngineRegistry(
        MarketSessionResourcePolicy(
            settings=Settings(artifacts_dir=str(tmp_path)),
            forced_session_state=state,
        )
    )


def test_lab_gets_priority_in_regular_market(tmp_path) -> None:
    decision = _registry(tmp_path, SessionState.REGULAR_MARKET).request_engine(
        EngineJobRequest(owner="lab", job_type="lab_execution")
    )

    assert decision.allowed is True
    assert decision.priority == "HIGH"


def test_research_gets_priority_market_closed(tmp_path) -> None:
    decision = _registry(tmp_path, SessionState.MARKET_CLOSED).request_engine(
        EngineJobRequest(owner="research", job_type="research_heavy", heavy=True)
    )

    assert decision.allowed is True
    assert decision.priority == "HIGH"


def test_research_heavy_blocked_in_regular_market_with_reason(tmp_path) -> None:
    decision = _registry(tmp_path, SessionState.REGULAR_MARKET).request_engine(
        EngineJobRequest(owner="research", job_type="research_heavy", heavy=True)
    )

    assert decision.allowed is False
    assert decision.priority == "BLOCKED"
    assert decision.deny_reason


def test_daily_watchlist_after_close_gets_priority(tmp_path) -> None:
    decision = _registry(tmp_path, SessionState.POST_MARKET).request_engine(
        EngineJobRequest(owner="daily_watchlist", job_type="daily_watchlist_reeval")
    )

    assert decision.allowed is True
    assert decision.priority == "HIGH"


def test_unknown_session_fails_closed(tmp_path) -> None:
    decision = _registry(tmp_path, SessionState.UNKNOWN).request_engine(
        EngineJobRequest(owner="lab", job_type="lab_execution")
    )

    assert decision.allowed is False
    assert decision.deny_reason == "session state unknown; fail closed"


def test_simultaneous_high_priority_contention_resolves_to_session_owner(tmp_path) -> None:
    decisions = _registry(tmp_path, SessionState.REGULAR_MARKET).arbitrate(
        [
            EngineJobRequest(owner="lab", job_type="lab_execution"),
            EngineJobRequest(owner="research", job_type="research_light"),
        ]
    )

    by_owner = {decision.owner: decision for decision in decisions}
    assert by_owner["lab"].allowed is True
    assert by_owner["research"].priority == "LOW"


def test_unknown_engine_id_fails_closed(tmp_path) -> None:
    decision = _registry(tmp_path, SessionState.POST_MARKET).request_engine(
        EngineJobRequest(
            owner="daily_watchlist",
            job_type="daily_watchlist_reeval",
            engine_id="UNKNOWN",
        )
    )

    assert decision.allowed is False
    assert decision.priority == "BLOCKED"
    assert decision.deny_reason == DENY_UNKNOWN_ENGINE


def test_scheduler_plan_carries_budget_priority_and_deny_reason(tmp_path) -> None:
    allowed_policy = MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path)),
        forced_session_state=SessionState.POST_MARKET,
    )
    blocked_policy = MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path)),
        forced_session_state=SessionState.UNKNOWN,
    )

    allowed = plan_daily_watchlist_scheduler_run(resource_policy=allowed_policy)
    blocked = plan_daily_watchlist_scheduler_run(resource_policy=blocked_policy)

    assert allowed.allowed is True
    assert allowed.resource_policy_priority == "HIGH"
    assert allowed.resource_remaining is not None
    assert allowed.as_scheduler_metadata()["resource_budget"]["max_symbols"] == 120
    assert blocked.allowed is False
    assert blocked.deny_reason == "resource_policy:session state unknown; fail closed"


def test_scheduler_plan_requires_resource_policy() -> None:
    decision = plan_daily_watchlist_scheduler_run(
        resources={
            "max_symbols": 120,
            "market_data_requests": 10,
            "cpu_seconds": 30,
            "storage_mb": 16,
            "parallel_slots": 1,
        }
    )

    assert decision.allowed is False
    assert decision.deny_reason == "resource_policy_missing"
    assert decision.session_state == "UNKNOWN"


def test_registry_plan_uses_attached_resource_policy(tmp_path) -> None:
    registry = _registry(tmp_path, SessionState.UNKNOWN)

    decision = registry.plan(
        "daily_watchlist_fast_v1",
        resources={
            "max_symbols": 120,
            "market_data_requests": 10,
            "cpu_seconds": 30,
            "storage_mb": 16,
            "parallel_slots": 1,
        },
    )

    assert decision.allowed is False
    assert decision.deny_reason == "resource_policy:session state unknown; fail closed"
    assert decision.session_state == "UNKNOWN"
