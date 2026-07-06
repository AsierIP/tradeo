from __future__ import annotations

from tradeo.core.config import Settings
from tradeo.modules.resource_policy.enforcement import assert_job_allowed
from tradeo.modules.resource_policy.market_session_resource_policy import (
    JobType,
    MarketSessionResourcePolicy,
    SessionState,
)


def _policy(tmp_path, state: str) -> MarketSessionResourcePolicy:
    return MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path)),
        forced_session_state=state,
    )


def test_settings_and_example_default_paper_auto_submit_false() -> None:
    assert Settings().laboratory_auto_submit_paper_orders is False
    assert "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false" in open(
        ".env.example",
        encoding="utf-8",
    ).read()


def test_unknown_session_fails_closed(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.UNKNOWN),
    )

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.can_submit_orders is False


def test_regular_market_blocks_research_heavy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.REGULAR_MARKET),
    )

    assert decision.allowed is False
    assert "Research heavy" in decision.deny_reason or "Research" in decision.deny_reason


def test_market_closed_allows_research_heavy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.MARKET_CLOSED),
    )

    assert decision.allowed is True
    assert decision.priority == "HIGH"


def test_paper_submit_is_never_authorized_by_resource_policy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.PAPER_SUBMIT,
        "daily_watchlist",
        policy=_policy(tmp_path, SessionState.REGULAR_MARKET),
    )

    assert decision.allowed is False
    assert decision.can_submit_orders is False
    assert "paper submit is blocked" in str(decision.deny_reason)
