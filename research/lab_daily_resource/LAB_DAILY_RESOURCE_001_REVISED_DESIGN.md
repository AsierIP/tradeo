# LAB_DAILY_RESOURCE_001 Revised Design

## Accepted Changes

- Added top-level budget fields to `/api/resource-policy/status`.
- Added Daily artifact lookup for `artifacts/runtime/daily_swing/setup_watchlist/latest.json`.
- Kept all Daily endpoint methods read-only.
- Preserved existing broker submit paths untouched.
- Frontend shows watchlist as passive Lab Daily metadata.

## Rejected Changes

- No write/admin mutation endpoint for Daily setups.
- No auto-promotion to FoxHunter.
- No direct paper/live enablement from `entry_ready`.
- No new heavy analysis engine.

## Conflicts Resolved

- Resource gate vs budget naming: gate remains `MarketSessionResourcePolicy`; budget policy is available as `MarketSessionBudgetPolicy` and direct module class.
- Daily state machine: direct transitions to `entered` are blocked; only `entry_ready -> entered` is representable for external reconciliation metadata.

## Remaining Unknowns

- Full pytest/ruff/frontend build must be run in the project dependency environment.
