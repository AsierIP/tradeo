# Agent E Integration Plan

## Objective

Integrate A-D without relaxing gates, opening order paths, or mixing Daily/Lab/Intraday/FoxHunter metrics.

## Files

- `research/lab_daily_resource/*`
- final contracts, red-team and QA reports.

## Plan

1. Keep implementation read-only except runtime artifacts.
2. Register routers under `/api`.
3. Preserve existing order submit paths unchanged.
4. Keep Daily watchlist artifacts under ignored `artifacts/runtime`.
5. Use frontend as passive status/contract display only.

## Blockers Watched

- Missing dependencies in local parent shell.
- `.env.example` inherited paper auto-submit default.
- Concurrent agent writes requiring final reconciliation.

## Fail-Safe

Decision may be READY_WITH_UI_PLACEHOLDER only if safety/compile/static checks pass and missing full test environment is documented.
