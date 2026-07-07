# T-LAB-DAILY-RESOURCE-004 Wrapper Inventory

Scope: historical wrappers and launch surfaces that can start heavy jobs, research, scans, runners, workers, Lab tasks, paper probes, previews, order-adjacent flows, or notification cron payloads.

Structured artifacts:

- `research/lab_daily_resource/lab_daily_resource_004_wrapper_inventory.csv`
- `research/lab_daily_resource/lab_daily_resource_004_wrapper_inventory.json`

## Method

Searched direct launch surfaces in `scripts/`, `backend/tradeo/tasks/worker.py`, Docker/systemd/ops wrappers, API routers, and `research/audit_bridge/`. The `path` column may include `::function` or `#service` when a single file exposes multiple scheduler/API surfaces.

Policy interpretation follows the current resource policy:

- `research_heavy`, `large_scanner`, and `heavy_backtest`: blocked pre-market and regular market; allowed post-market and market-closed.
- `lab_paper_probe`: allowed pre-market and regular market; blocked post-market and market-closed.
- `paper_submit` and `live`: blocked in all listed sessions.
- `mixed`: policy-dependent because the wrapper starts multiple child surfaces.

## High-Risk Coverage Findings

- `docker-compose.yml#worker` and `backend/tradeo/tasks/worker.py::main` start a mixed APScheduler surface. The rollout applies per-job enforcement to scanner, self-improvement/backtest-like research, discovery, novel matching, research director, intraday data sync/research, process-pool research, and candidate scan child jobs.
- Admin heavy-launch API routes that bypass the worker now use route-level resource policy guards for `/research/run-discovery`, `/research/match-current`, `/research/director/run`, `/scan`, `/backtests/run`, and `/self-improvement/run`.
- Standalone heavy scripts now have early policy gates before provider, process-pool, capacity, GAP, or Daily Swing backtest work. Shell-only supervision wrappers such as `research_forever.sh` remain documentation/operator surfaces and do not receive order authority.
- Lab shadow wrappers are safer than average because they force read-only/no-paper/no-live env flags and write no-order summaries, but they do not yet record a `lab_paper_probe` resource decision.
- GAP runners still self-block hidden `orders`, `preview`, `signals`, `paper`, `live`, and `ibkr` flags, and now also gate heavy matrix/backtest CPU around market sessions.

## Inventory Summary

Full rows are in both the CSV and JSON. The JSON also carries the policy basis, row count, decision, and cross-review note.

Counts by broad status:

- Enforced by current resource policy: scheduler/worker heavy jobs, admin heavy-launch routes, intraday/capacity runners, cache/universe/scanner CLIs, GAP runners, and Daily Swing historical backtest/audit wrappers.
- Legacy safety gated without Daily resource policy: Lab/Fox entry scanners, Lab shadow wrappers, read-only IBKR probes.
- Self-blocked order/preview flags plus resource policy: daily GAP validation and matrix runners.
- No submit-path rollout: order-adjacent submit/preview routes remain governed by existing submit gates and were not granted authority.
- Mixed stack starters: Docker backend/worker, backend Docker CMD, systemd service, deploy script.

## Cross-Review Note For B

Risks B covered in this rollout: API route bypasses for heavy launch routes, classic worker heavy jobs, standalone scripts that hit providers or run heavy backtests, and intraday data sync. Order-adjacent submit routes remain intentionally outside scope and receive no new authority.

## Partial Decision

INVENTORY_COMPLETE

Reason: inventory is complete for the T-004 rollout scope and now matches the implemented scheduler/worker/research/lab wrapper enforcement state.
