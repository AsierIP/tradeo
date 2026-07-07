# LAB_DAILY_RESOURCE_004 Separation Audit

Task: `T-LAB-DAILY-RESOURCE-004`
Repo: `/home/vboxuser/tradeo-worktrees/director-control-loop-operability`
Branch: `feature/lab-daily-resource-004-enforcement-rollout`
Generated: `2026-07-07`
Decision: `SEPARATION_PASS`

## Scope

This audit covers the final T-004 rollout state: shared enforcement, worker/scheduler wrappers, admin heavy-launch routes, standalone heavy scripts, Daily Watchlist, Lab Paper Probe, FoxHunter promotion safety, and UI/API write surfaces.

No timers, Lab Paper Probe one-shots, real `.env`, runtime artifacts, `MEMORY.md`, `memory/`, submit paths, paper submit paths, or live paths were changed.

## Findings

| Check | Result | Evidence |
| --- | --- | --- |
| Daily Watchlist does not send orders | PASS | Daily setup artifacts remain non-submitting and red-team asserts `entry_ready` does not call submit or emit broker ids. |
| Lab Paper Probe does not receive submit authority from Resource Policy | PASS | `lab_paper_probe` may be prioritized by policy, but `can_submit_orders=false`; paper readiness remains dry-run-only and gated by its own runner. |
| Research heavy cannot run in `REGULAR_MARKET` | PASS | Policy blocks `research_heavy`, `heavy_backtest`, and `large_scanner` in RTH; worker, route, and script guards check before heavy/provider/process-pool/backtest work. |
| Lab does not consume Research budgets during `MARKET_CLOSED` except maintenance-sized capacity | PASS | Market-closed policy keeps Lab low capacity, Research high capacity, and blocks paper/live submit. |
| Daily after-close reevaluation allowed in `POST_MARKET` / `MARKET_CLOSED` | PASS | Daily reevaluation remains allowed and prioritized after close while submit resources stay blocked. |
| FoxHunter does not auto-promote | PASS | No FoxHunter auto-promotion or live button was added; existing production-gate/human-approval behavior remains unchanged. |
| No new signal/preview/order output | PASS | Resource Policy and Daily surfaces remain read-only; submit/order-adjacent paths were not expanded. |
| Daily/Lab/Intraday/FoxHunter metrics remain separated | PASS | Tests and static checks confirm Daily artifacts do not mix intraday/live/broker fields; module dashboards remain separated. |

## Cross-Review Note on B Risks

B risk is closed for this rollout scope. The final state adds shared machine-readable deny reasons, worker guards, admin heavy-launch route guards, script guards, fast-chart policy wiring, and tests that reconcile the deny reason contract.

Order-adjacent submit/preview paths remain intentionally outside the rollout and were not granted authority.

## Partial Decision

`SEPARATION_PASS`

No blocker was found for Daily orderlessness, Lab Paper Probe authority, API/UI write safety, FoxHunter promotion safety, metric separation, or Research heavy RTH blocking in the rollout scope.
