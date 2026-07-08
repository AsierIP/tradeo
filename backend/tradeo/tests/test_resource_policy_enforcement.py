from __future__ import annotations

from pathlib import Path

from tradeo.core.config import Settings
from tradeo.modules.resource_policy.enforcement import (
    DENY_INTRADAY_FROZEN_DAILY_FOCUS,
    DENY_PAPER_SUBMIT,
    DENY_POLICY_DENIED,
    DENY_POLICY_MISSING,
    DENY_SESSION_UNKNOWN,
    assert_job_allowed,
)
from tradeo.modules.resource_policy.market_session_resource_policy import (
    JobType,
    MarketSessionResourcePolicy,
    SessionState,
)


def _policy(tmp_path, state: str, *, focus_mode: str = "all") -> MarketSessionResourcePolicy:
    return MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path), focus_mode=focus_mode),
        forced_session_state=state,
    )


def test_settings_and_example_default_paper_auto_submit_false() -> None:
    settings = Settings(
        focus_mode="daily_only",
        laboratory_auto_submit_paper_orders=False,
    )

    assert settings.laboratory_auto_submit_paper_orders is False
    assert settings.focus_mode == "daily_only"
    env_example = next(
        (
            parent / ".env.example"
            for parent in Path(__file__).resolve().parents
            if (parent / ".env.example").exists()
        ),
        None,
    )
    if env_example is None:
        return
    example_text = env_example.read_text(encoding="utf-8")
    assert "TRADEO_FOCUS_MODE=daily_only" in example_text
    assert "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false" in example_text


def test_unknown_session_fails_closed(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.UNKNOWN),
    )

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.can_submit_orders is False
    assert decision.deny_reason == DENY_SESSION_UNKNOWN


def test_explicit_unknown_session_argument_fails_closed_before_policy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        session_state=" unknown ",
        policy=_policy(tmp_path, SessionState.MARKET_CLOSED),
    )

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.deny_reason == DENY_SESSION_UNKNOWN


def test_missing_policy_fails_closed() -> None:
    decision = assert_job_allowed(JobType.RESEARCH_HEAVY, "research")

    assert decision.allowed is False
    assert decision.session_state == SessionState.UNKNOWN
    assert decision.deny_reason == DENY_POLICY_MISSING


def test_regular_market_blocks_research_heavy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.REGULAR_MARKET),
    )

    assert decision.allowed is False
    assert str(decision.deny_reason).startswith(f"{DENY_POLICY_DENIED}:")


def test_market_closed_allows_research_heavy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.MARKET_CLOSED),
    )

    assert decision.allowed is True
    assert decision.priority == "HIGH"


def test_daily_focus_freeze_reason_propagates_through_enforcement(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.MARKET_CLOSED, focus_mode="daily_only"),
    )
    paper = assert_job_allowed(
        JobType.PAPER_SUBMIT,
        "daily_watchlist",
        policy=_policy(tmp_path, SessionState.REGULAR_MARKET, focus_mode="daily_only"),
    )

    assert decision.allowed is False
    assert decision.deny_reason == DENY_INTRADAY_FROZEN_DAILY_FOCUS
    assert decision.session_state == SessionState.MARKET_CLOSED
    assert decision.to_dict()["focus_mode"] == "daily_only"
    assert decision.to_dict()["intraday_freeze_active"] is True
    assert paper.allowed is False
    assert paper.deny_reason == DENY_INTRADAY_FROZEN_DAILY_FOCUS


def test_paper_submit_is_never_authorized_by_resource_policy(tmp_path) -> None:
    decision = assert_job_allowed(
        JobType.PAPER_SUBMIT,
        "daily_watchlist",
        policy=_policy(tmp_path, SessionState.REGULAR_MARKET),
    )

    assert decision.allowed is False
    assert decision.can_submit_orders is False
    assert decision.deny_reason == DENY_PAPER_SUBMIT
