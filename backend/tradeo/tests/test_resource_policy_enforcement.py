from __future__ import annotations

from pathlib import Path

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
    repo_root = Path(__file__).resolve().parents[3]
    env_example = repo_root / ".env.example"
    assert "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false" in env_example.read_text(
        encoding="utf-8"
    )


def test_unknown_session_fails_closed(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.UNKNOWN),
    )

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.can_submit_orders is False


def test_explicit_unknown_session_argument_fails_closed_before_policy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        session_state=" unknown ",
        policy=_policy(tmp_path, SessionState.MARKET_CLOSED),
    )

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.deny_reason == "session state unknown; fail closed"


def test_missing_policy_fails_closed() -> None:
    decision = assert_job_allowed(JobType.RESEARCH_HEAVY, "research")

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.deny_reason == "resource policy missing; fail closed"


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
