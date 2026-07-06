# T-LAB-DAILY-RESOURCE-001 - Agent E QA Report

Date: 2026-07-06
Agent: E - Integrator / Red-Team / QA
Repo: `/tmp/tradeo-lab-daily-resource-001`
Branch: `feature/lab-daily-resource-001`
Base commit at initial inspection: `f47b76927d37034a239680312e212142d3f4cdd1`

## Scope

Review integration, safety contracts/docs under `research/lab_daily_resource`,
red-team checklist, QA plan, summarized risks, recommended validations, and a
tentative final decision.

No live trading, broker order paths, `gh`, push, merge, container startup, or
order endpoints were used. The only intentional file change by Agent E is this
QA report. Other implementation files changed concurrently during review and
were inspected but not edited.

## Concurrent Worktree Snapshot

The branch was initially identical to `origin/main` and clean. During review,
other agents added/modified implementation files. Current relevant uncommitted
state observed by Agent E:

- Modified: `backend/tradeo/core/config.py`, `backend/tradeo/main.py`,
  `frontend/app/page.tsx`.
- Added/untracked: `backend/tradeo/modules/resource_policy/`,
  `backend/tradeo/modules/fast_chart_analysis/`,
  `backend/tradeo/modules/daily_swing/setup_watchlist.py`,
  `backend/tradeo/routers/daily.py`,
  `backend/tradeo/routers/resource_policy.py`,
  several backend tests, and Agent A/E reports under
  `research/lab_daily_resource`.

Because the worktree was changing while QA ran, this report is a snapshot review,
not a final integration acceptance.

## Executive Decision

Tentative decision: **NO-GO / BLOCKED**.

Reasons:

- Integration is not stable: files changed concurrently during review.
- Full validation could not run: `backend/.venv/bin/python` is missing, system
  Python has no `pytest`, system Python has no `pydantic`, and frontend
  `node_modules` are absent.
- Read-only operability preflight returned `BLOCKED` from `.env.example` because
  `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`; `.env` is also absent, so
  `docker compose config` failed.
- Frontend has a likely TypeScript blocker: `DailySetupWatchlistItem` is declared
  twice in `frontend/app/page.tsx`.
- No consolidated final task contract/decision from all A-D scopes was available
  for Agent E to approve.

## Positive Findings

- The new resource-policy code is designed as a pure/read-only gate and marks
  `order.preview`, `order.paper`, `order.live`, and `signal.output` as prohibited.
- Daily setup watchlist artifacts explicitly set `orders_allowed=false`,
  `paper_allowed=false`, `live_allowed=false`, and `submit_order_called=false`.
- New routers expose GET/read-only status surfaces with explicit blocked actions.
- Static scan of the new modules found no `placeOrder` or broker order call.
- `python3 -m compileall -q` over the new backend modules/routers passed.
- `git diff --check` passed.

## Blocking Findings

1. **Read-only safety preflight is blocked.**
   - Command: `python3 scripts/check_tradeo_operability.py --json-only`
   - Result: `BLOCKED`
   - Reason: `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true` from
     `.env.example`.
   - Additional issue: `.env` missing, so `docker compose config` failed.
   - Live/order gates in the preflight summary remained closed, but this is not
     sufficient for read-only approval while paper auto-submit is enabled by
     default.

2. **Backend tests could not execute.**
   - `make test-safety` failed before tests with `backend/.venv/bin/python: not found`.
   - `python3 -m pytest ...` failed because system Python has no `pytest`.
   - Router import smoke with system Python failed because system Python has no
     `pydantic`.

3. **Frontend type risk in `frontend/app/page.tsx`.**
   - `DailySetupWatchlistItem` is declared twice with different shapes.
   - Frontend typecheck could not be executed because `frontend/node_modules` is
     missing, so this remains an unverified but likely compile blocker.

4. **Task-level docs are incomplete.**
   - Agent A report exists for market-session resource policy.
   - No final cross-agent integration decision, red-team closure, or A-D
     consolidated contract was present at the time of this QA snapshot.

## Red-Team Checklist

Minimum adversarial cases before approval:

- Missing or renamed task package: require `research/lab_daily_resource` to
  contain the task contract, agent reports, and final decision artifact.
- Prompt/config injection attempts that set:
  `TRADEO_TRADING_MODE=live`, `TRADEO_LIVE_TRADING_ENABLED=true`,
  `TRADEO_IBKR_READONLY=false`, `TRADEO_ALLOW_OPTIONS=true`,
  `TRADEO_ALLOW_MARGIN=true`, or any paper/live auto-submit flag.
- Resource-policy bypass: consumers must not acquire heavy/broker-adjacent
  resources without checking the policy.
- Unknown market-session state, calendar errors, unsupported market, and
  contradictory open/closed state must fail closed.
- During regular market hours, heavy research/backtests and IBKR historical or
  realtime refreshes must be blocked or explicitly budgeted by policy.
- Daily watchlist entry-ready state must not create signals, candidates, paper
  orders, live orders, or FoxHunter promotions.
- Paper-probe metadata must not be interpreted as permission to submit orders.
- Frontend must not display watchlist rows as executable signals or imply paper
  or live submission is enabled.
- Report bundles/logs must redact account IDs, keys, tokens, passwords, and
  credential-like values.
- Tests and QA commands must not start live systems, connect orders, or call
  broker/order endpoints.

## Recommended QA Plan

Gate 1 - Stabilize the worktree:

- Stop concurrent writes or hand off a stable snapshot.
- Remove or intentionally ignore generated `__pycache__` artifacts before final
  packaging.
- Confirm all intended A-D files are present and named.

Gate 2 - Safety contract:

- Resolve the `.env.example` versus read-only preflight conflict for
  `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`.
- Re-run `python3 scripts/check_tradeo_operability.py --json-only`.
- Require `OPERABLE_READ_ONLY` for read-only QA, or a separately authorized paper
  mode with explicit evidence.

Gate 3 - Backend validation:

- Provision backend dependencies.
- Run `make test-safety`.
- Run focused tests:
  - `test_resource_policy_market_session.py`
  - `test_market_session_resource_policy.py`
  - `test_fast_chart_engine_registry.py`
  - `test_daily_setup_watchlist.py`
- Run import smoke for the new routers under the same Python environment used by
  CI/runtime.

Gate 4 - Frontend validation:

- Remove or reconcile duplicate `DailySetupWatchlistItem` declarations.
- Run `npm install`/existing dependency setup if needed.
- Run `npx tsc --noEmit` or `npm run build`.
- Verify the daily watchlist panel consumes the actual `/daily/setup-watchlist`
  response shape.

Gate 5 - Integration contract:

- Add a consolidated `T-LAB-DAILY-RESOURCE-001` final decision artifact under
  `research/lab_daily_resource`.
- Document allowed resources by session, prohibited actions, rollback/quarantine
  steps, and exact validation evidence.
- PASS only after safety preflight and tests pass on a stable snapshot.

## Final Tentative Decision

**NO-GO / BLOCKED** for merge/approval today.

The current direction looks safety-conscious and read-only, but the branch is
not yet acceptance-ready because the worktree is unstable, test environments are
missing, preflight blocks read-only approval, and frontend/backend validation has
not completed.
