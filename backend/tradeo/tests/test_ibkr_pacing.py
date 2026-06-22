from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tradeo.services.ibkr_pacing import IbkrPacingBudget, PacingRequest, PacingRule


def test_ibkr_pacing_budget_never_exceeds_window() -> None:
    now = datetime(2026, 6, 22, 14, 0, tzinfo=UTC)
    budget = IbkrPacingBudget(rules={"historical": PacingRule(capacity=2, window_seconds=600)})

    first = budget.try_acquire("historical", "SOUN", "5m", now=now)
    second = budget.try_acquire("historical", "RXRX", "5m", now=now + timedelta(seconds=1))
    blocked = budget.try_acquire("historical", "UPST", "5m", now=now + timedelta(seconds=2))

    assert first.allowed is True
    assert second.allowed is True
    assert blocked.allowed is False
    assert blocked.reason == "pacing_exhausted"
    assert blocked.degraded_to_shadow_safe is True
    assert budget.metrics(now=now + timedelta(seconds=2))["new_entries_allowed"] is False


def test_ibkr_pacing_plan_prioritizes_open_portfolio_and_dedupes() -> None:
    now = datetime(2026, 6, 22, 14, 0, tzinfo=UTC)
    budget = IbkrPacingBudget(rules={"historical": PacingRule(capacity=1, window_seconds=600)})

    plan = budget.plan_requests(
        [
            PacingRequest(symbol="SOUN", timeframe="5m", priority=1),
            PacingRequest(symbol="SOUN", timeframe="5m", priority=5),
            PacingRequest(symbol="RXRX", timeframe="5m", portfolio_open=True),
        ],
        now=now,
    )

    assert [request.symbol for request in plan.allowed] == ["RXRX"]
    assert {request.symbol for request, _ in plan.skipped} == {"SOUN"}


def test_ibkr_pacing_reserves_daily_budget_from_intraday_scope() -> None:
    now = datetime(2026, 6, 22, 14, 0, tzinfo=UTC)
    budget = IbkrPacingBudget(
        rules={"historical": PacingRule(capacity=3, window_seconds=600, daily_reserved=1)}
    )

    assert budget.try_acquire("historical", "A", "5m", now=now).allowed is True
    assert budget.try_acquire("historical", "B", "5m", now=now).allowed is True
    blocked = budget.try_acquire("historical", "C", "5m", now=now)

    assert blocked.allowed is False
    assert blocked.reason == "daily_budget_reserved"
    daily = budget.try_acquire("historical", "SPY", "1d", scope="daily", now=now)
    assert daily.allowed is True
