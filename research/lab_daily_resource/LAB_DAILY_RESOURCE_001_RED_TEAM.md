# LAB_DAILY_RESOURCE_001 Red Team

Date: 2026-07-06

## Result

Status: PASS_WITH_RESIDUAL_WARNINGS

The integration was attacked against the mandatory cases. No new live, paper submit, broker submit or FoxHunter promotion path was found in the new modules/endpoints.

## Mandatory Cases

- Research heavy job during REGULAR_MARKET: blocked by `MarketSessionBudgetPolicy` and engine registry.
- Lab job during MARKET_CLOSED: low/maintenance only; Lab Paper Probe blocked.
- Daily setup `entry_ready` attempting direct order: no submit path; metadata carries `submits_order=false`.
- Endpoint write accidental: new Daily endpoints are GET-only; POST returns 405 in tests.
- Setup with `lookahead_risk`: non-recoverable and not admitted.
- Setup with insufficient reward/risk: not admitted.
- Fast engine Lab and Research HIGH simultaneously: registry routes through policy; Research heavy blocked during REGULAR_MARKET.
- Runtime artifact tracked accidentally: artifact paths are under ignored `artifacts/runtime`.
- Endpoint exposing secrets: endpoint tests and static scan check redaction/flags.
- Daily metrics mixed with Lab/FoxHunter: Daily payload remains `timeframe=1d`, watchlist-only; UI panel is passive.
- Auto-promotion to FoxHunter: blocked by contract and no implementation path.
- Paper/live activated by error: not activated; existing order paths unchanged.

## Residual Warnings

- `.env.example` inherited `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`; this task did not change existing operational defaults.
- Frontend build produced Next lockfile SWC patch warnings but exited 0 and changed no versioned files.
