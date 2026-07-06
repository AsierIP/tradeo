from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradeo.modules.resource_policy import (
    MarketSessionBudgetPolicy,
    MarketSessionResourcePolicy as ExportedMarketSessionResourcePolicy,
)
from tradeo.modules.resource_policy.market_session import (
    RESOURCE_ARTIFACT_WRITE,
    RESOURCE_IBKR_HISTORICAL_DATA,
    RESOURCE_LAB_BACKTEST,
    RESOURCE_LIVE_ORDER,
    RESOURCE_LOCAL_CACHE_READ,
    RESOURCE_LOCAL_CACHE_WRITE,
    RESOURCE_MARKET_DATA_REFRESH,
    RESOURCE_MARKET_SESSION_STATUS,
    RESOURCE_PAPER_ORDER,
    RESOURCE_REPORT_WRITE,
    MarketSessionResourcePolicy,
)
from tradeo.modules.resource_policy.market_session_resource_policy import (
    MarketSessionResourcePolicy as BudgetMarketSessionResourcePolicy,
)

NY = ZoneInfo("America/New_York")


def _open_session() -> dict[str, object]:
    return {
        "market": "us_equities",
        "timezone": "America/New_York",
        "regular_session_open": True,
        "state": "regular_open",
        "checked_at": "2026-07-06T10:00:00-04:00",
        "regular_hours": "09:30-16:00",
        "holiday": None,
    }


def _closed_session() -> dict[str, object]:
    return {
        **_open_session(),
        "regular_session_open": False,
        "state": "market_closed",
        "checked_at": "2026-07-06T18:00:00-04:00",
    }


def test_resource_policy_package_exports_gate_and_budget_policy() -> None:
    assert ExportedMarketSessionResourcePolicy is MarketSessionResourcePolicy
    assert MarketSessionBudgetPolicy is BudgetMarketSessionResourcePolicy


def test_market_session_policy_open_session_allows_only_safe_local_resources() -> None:
    policy = MarketSessionResourcePolicy(session_provider=None)

    decision = policy.evaluate(
        [
            RESOURCE_MARKET_SESSION_STATUS,
            RESOURCE_LOCAL_CACHE_READ,
            RESOURCE_LOCAL_CACHE_WRITE,
            RESOURCE_MARKET_DATA_REFRESH,
            RESOURCE_PAPER_ORDER,
        ],
        market_session=_open_session(),
    )

    assert decision.decision == "RESOURCE_POLICY_PARTIAL_ALLOW"
    assert decision.fail_closed is False
    assert decision.allowed_resources == (
        RESOURCE_LOCAL_CACHE_READ,
        RESOURCE_MARKET_SESSION_STATUS,
    )
    assert RESOURCE_LOCAL_CACHE_WRITE in decision.blocked_resources
    assert RESOURCE_MARKET_DATA_REFRESH in decision.blocked_resources
    assert RESOURCE_PAPER_ORDER in decision.blocked_resources
    assert "regular_session_resource_protected" in decision.block_reasons[RESOURCE_MARKET_DATA_REFRESH]
    assert f"prohibited_resource:{RESOURCE_PAPER_ORDER}" in decision.block_reasons[RESOURCE_PAPER_ORDER]


def test_market_session_policy_closed_session_allows_offline_lab_resources() -> None:
    policy = MarketSessionResourcePolicy(session_provider=None)

    decision = policy.evaluate(
        [
            RESOURCE_LOCAL_CACHE_READ,
            RESOURCE_LOCAL_CACHE_WRITE,
            RESOURCE_ARTIFACT_WRITE,
            RESOURCE_REPORT_WRITE,
            RESOURCE_LAB_BACKTEST,
            RESOURCE_IBKR_HISTORICAL_DATA,
            RESOURCE_LIVE_ORDER,
        ],
        market_session=_closed_session(),
    )

    assert decision.decision == "RESOURCE_POLICY_PARTIAL_ALLOW"
    assert decision.fail_closed is False
    assert decision.allowed_resources == (
        RESOURCE_ARTIFACT_WRITE,
        RESOURCE_IBKR_HISTORICAL_DATA,
        RESOURCE_LAB_BACKTEST,
        RESOURCE_LOCAL_CACHE_READ,
        RESOURCE_LOCAL_CACHE_WRITE,
        RESOURCE_REPORT_WRITE,
    )
    assert decision.blocked_resources == (RESOURCE_LIVE_ORDER,)
    assert f"prohibited_resource:{RESOURCE_LIVE_ORDER}" in decision.block_reasons[RESOURCE_LIVE_ORDER]


def test_market_session_policy_fail_closed_when_session_provider_fails() -> None:
    def broken_provider(now: datetime | None) -> dict[str, object]:
        raise RuntimeError("calendar unavailable")

    policy = MarketSessionResourcePolicy(session_provider=broken_provider)

    decision = policy.evaluate(
        [RESOURCE_LOCAL_CACHE_READ, RESOURCE_LAB_BACKTEST],
        now=datetime(2026, 7, 6, 10, 0, tzinfo=NY),
    )

    assert decision.decision == "RESOURCE_POLICY_FAIL_CLOSED"
    assert decision.allowed_resources == ()
    assert decision.blocked_resources == (RESOURCE_LAB_BACKTEST, RESOURCE_LOCAL_CACHE_READ)
    assert decision.fail_closed is True
    assert "market_session_provider_error:RuntimeError" in decision.reason_codes


def test_market_session_policy_fail_closed_on_inconsistent_open_state() -> None:
    policy = MarketSessionResourcePolicy(session_provider=None)

    decision = policy.evaluate(
        [RESOURCE_LOCAL_CACHE_READ],
        market_session={**_open_session(), "state": "market_closed"},
    )

    assert decision.decision == "RESOURCE_POLICY_FAIL_CLOSED"
    assert decision.allowed_resources == ()
    assert decision.blocked_resources == (RESOURCE_LOCAL_CACHE_READ,)
    assert "market_session_open_state_mismatch" in decision.reason_codes


def test_market_session_policy_blocks_unknown_resources_without_fail_open() -> None:
    policy = MarketSessionResourcePolicy(session_provider=None)

    decision = policy.evaluate(
        [RESOURCE_LOCAL_CACHE_READ, "gpu.cluster.write"],
        market_session=_closed_session(),
    )

    assert decision.fail_closed is False
    assert decision.allowed_resources == (RESOURCE_LOCAL_CACHE_READ,)
    assert decision.blocked_resources == ("gpu.cluster.write",)
    assert "unknown_resource:gpu.cluster.write" in decision.block_reasons["gpu.cluster.write"]
