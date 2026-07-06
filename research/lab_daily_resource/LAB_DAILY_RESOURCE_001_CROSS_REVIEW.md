# LAB_DAILY_RESOURCE_001 Cross Review

## Matrix Results

- A reviewed B/D: Daily entry-ready must not become an order path; fast engine must fail closed on UNKNOWN.
- B reviewed A/C: Resource endpoint must not expose secrets; Daily endpoints must be GET-only.
- C reviewed B/D: API payload needs explicit `read_only`, blocked actions and no write contract; registry must return deny reason.
- D reviewed A/C: Research heavy must be blocked during regular market; API must show enough policy state for operators.
- E reviewed all: concurrent writes reconciled; frontend duplicate-type risk checked; runtime artifact paths aligned to ignored directories.

## Contradictions Detected

- Two resource-policy concepts existed: pure resource gate and session budget. Kept both: exported gate plus `MarketSessionBudgetPolicy`.
- Daily artifact path initially diverged. Final path includes `artifacts/runtime/daily_swing/setup_watchlist/latest.json`.
- Daily status model initially blocked `entered` entirely; final state machine permits only `entry_ready -> entered`, while direct transitions remain blocked.

## Safety Risks

- Existing `.env.example` still has `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`; this task did not change submit behavior.
- Full pytest/ruff/frontend build were unavailable in parent shell.

## Missing Tests / Recommendations

- Run full CI in backend dev environment.
- Add runtime consumer integration before enabling any scheduler enforcement.
- Add Playwright/UI test when frontend dependencies are available.
