# T-LAB-DAILY-RESOURCE-001 Agent A - Market Session Resource Policy

Status: implemented as fail-closed policy contract; no runtime integration, no live/orders.

## Objective

Provide a pure market-session resource gate for lab and research workloads. The policy protects regular US equity market hours from heavy or broker-adjacent resource use, allows offline lab resources when the market is closed, and fails closed when the session state cannot be trusted.

## Files

- `backend/tradeo/modules/resource_policy/__init__.py`
- `backend/tradeo/modules/resource_policy/market_session.py`
- `backend/tradeo/tests/test_resource_policy_market_session.py`

## Contract

`MarketSessionResourcePolicy.evaluate(requested_resources, market_session=None, now=None)` returns a `ResourcePolicyDecision` dataclass with:

- `decision`: `RESOURCE_POLICY_ALLOW`, `RESOURCE_POLICY_PARTIAL_ALLOW`, `RESOURCE_POLICY_BLOCKED`, or `RESOURCE_POLICY_FAIL_CLOSED`
- `allowed_resources` / `blocked_resources`
- `reason_codes` and per-resource `block_reasons`
- `market_session`
- `fail_closed`

The policy accepts a supplied `market_session` mapping or calls an injectable `session_provider` compatible with `tradeo.services.market_session.market_session_status`.

The package export keeps this gate as `tradeo.modules.resource_policy.MarketSessionResourcePolicy`.
Concurrent budget work in `market_session_resource_policy.py` remains available as
`tradeo.modules.resource_policy.MarketSessionBudgetPolicy`.

## Fail-Safe

- Missing provider, provider exceptions, missing fields, unsupported market, and contradictory `regular_session_open`/`state` combinations return `RESOURCE_POLICY_FAIL_CLOSED`.
- Unknown resources are denied.
- `order.preview`, `order.paper`, `order.live`, and `signal.output` are always prohibited even if a custom allowlist includes them.
- During `regular_open`, session-sensitive broker/market-data refresh resources are denied.

## Risks

- This is a contract-only implementation; consumers must explicitly call it before acquiring shared resources.
- The default session model follows the existing `market_session_status` schema and supports `regular_open`, `market_closed`, and `market_holiday`.
- Concurrent B/D context appeared in the worktree while Agent A was running. The package export was reconciled so D-style callers using `evaluate(...)` and B-style budget callers using `MarketSessionBudgetPolicy` can coexist.
- Existing concurrent endpoint tests still disagree on the top-level `/resource-policy/status` response shape; resolving that router contract is outside Agent A's module-only change.

## Tests

Focused tests cover:

- Open-session safe local allowlist
- Closed-session offline lab allowlist
- Provider failure fail-closed
- Inconsistent session payload fail-closed
- Unknown resource denial without fail-open
