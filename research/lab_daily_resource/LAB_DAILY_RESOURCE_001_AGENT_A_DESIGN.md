# Agent A Design - Market Session Resource Policy

## Objective

Centralize session-aware resource budgets for Lab, Research, Daily watchlist and Lab Paper Probe.

## Files

- `backend/tradeo/modules/resource_policy/market_session_resource_policy.py`
- `backend/tradeo/modules/resource_policy/market_session.py`
- `backend/tradeo/routers/resource_policy.py`
- resource policy tests.

## Contracts

- Input: current timestamp or injected session/calendar provider.
- Output: session state, priorities, budgets, blocked job types, deny reasons and public read-only status.

## Risks

- Calendar uncertainty causing fail-open.
- Research heavy jobs contending with Lab during regular market.
- Endpoint accidentally exposing settings secrets.

## Tests

- PRE_MARKET, REGULAR_MARKET, POST_MARKET, MARKET_CLOSED, WEEKEND_OR_HOLIDAY, UNKNOWN.
- Research heavy blocked during REGULAR_MARKET.
- Latest artifact and endpoint exclude secrets.

## Fail-Safe

UNKNOWN session blocks Lab, Research heavy, Daily reevaluation, paper and live.
