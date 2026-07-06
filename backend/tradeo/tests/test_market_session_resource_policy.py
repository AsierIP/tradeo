from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tradeo.core.config import Settings
from tradeo.core.security import require_admin
from tradeo.modules.resource_policy.market_session_resource_policy import (
    JobType,
    MarketSessionResourcePolicy,
    SessionState,
)
from tradeo.routers.resource_policy import router as resource_policy_router

NY = ZoneInfo("America/New_York")


def _policy(tmp_path, state: str | None = None) -> MarketSessionResourcePolicy:
    return MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path)),
        forced_session_state=state,
    )


def test_pre_market_assigns_lab_readiness_priority(tmp_path) -> None:
    budget = _policy(tmp_path).current_budget(datetime(2026, 7, 6, 8, 0, tzinfo=NY))

    assert budget.session_state == SessionState.PRE_MARKET
    assert budget.lab_priority == "HIGH"
    assert budget.lab_paper_probe_priority == "HIGH"
    assert JobType.RESEARCH_HEAVY in budget.blocked_job_types


def test_regular_market_blocks_research_heavy_and_prioritizes_lab(tmp_path) -> None:
    policy = _policy(tmp_path)

    budget = policy.current_budget(datetime(2026, 7, 6, 10, 0, tzinfo=NY))
    decision = policy.decide_job(JobType.RESEARCH_HEAVY, datetime(2026, 7, 6, 10, 0, tzinfo=NY))

    assert budget.session_state == SessionState.REGULAR_MARKET
    assert budget.lab_priority == "HIGH"
    assert decision.allowed is False
    assert decision.priority == "BLOCKED"


def test_market_closed_assigns_research_high(tmp_path) -> None:
    budget = _policy(tmp_path).current_budget(datetime(2026, 7, 6, 21, 0, tzinfo=NY))

    assert budget.session_state == SessionState.MARKET_CLOSED
    assert budget.research_priority == "HIGH"
    assert budget.heavy_research_allowed is True
    assert budget.ibkr_write_allowed is False


def test_post_market_assigns_daily_reevaluation_high(tmp_path) -> None:
    budget = _policy(tmp_path).current_budget(datetime(2026, 7, 6, 17, 0, tzinfo=NY))

    assert budget.session_state == SessionState.POST_MARKET
    assert budget.daily_watchlist_priority == "HIGH"
    assert budget.daily_watchlist_reeval_allowed is True


def test_weekend_or_holiday_blocks_lab_execution(tmp_path) -> None:
    policy = _policy(tmp_path)
    decision = policy.decide_job(JobType.LAB_EXECUTION, datetime(2026, 7, 4, 12, 0, tzinfo=NY))

    assert decision.budget.session_state == SessionState.WEEKEND_OR_HOLIDAY
    assert decision.allowed is False


def test_lab_paper_probe_allowed_only_when_policy_allows(tmp_path) -> None:
    open_policy = _policy(tmp_path)
    closed_policy = _policy(tmp_path, SessionState.MARKET_CLOSED)

    assert open_policy.decide_job(JobType.LAB_PAPER_PROBE, datetime(2026, 7, 6, 10, 0, tzinfo=NY)).allowed is True
    assert closed_policy.decide_job(JobType.LAB_PAPER_PROBE).allowed is False


def test_unknown_session_fails_closed(tmp_path) -> None:
    budget = _policy(tmp_path, SessionState.UNKNOWN).current_budget()

    assert budget.session_state == SessionState.UNKNOWN
    assert budget.heavy_research_allowed is False
    assert budget.lab_paper_probe_allowed is False
    assert JobType.LIVE in budget.blocked_job_types


def test_artifact_latest_json_has_no_secrets(tmp_path) -> None:
    budget = _policy(tmp_path, SessionState.MARKET_CLOSED).current_budget()
    path = tmp_path / "runtime" / "resource_policy" / "latest.json"

    text = path.read_text(encoding="utf-8")
    assert budget.session_state in text
    assert "password" not in text.lower()
    assert "secret" not in text.lower()
    assert "account" not in text.lower()


def test_resource_policy_endpoint_read_only_without_secrets() -> None:
    app = FastAPI()
    app.include_router(resource_policy_router, prefix="/api")
    app.dependency_overrides[require_admin] = lambda: "test"

    response = TestClient(app).get("/api/resource-policy/status")

    assert response.status_code == 200
    payload = response.json()
    assert {
        "session_state",
        "priorities",
        "budgets",
        "blocked_job_types",
        "generated_at",
        "timezone",
        "reason",
    }.issubset(set(payload))
    assert payload["safety"]["secret_values_exposed"] is False
    assert "change-me" not in str(payload).lower()
