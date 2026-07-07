# T-LAB-DAILY-RESOURCE-004 Enforcement Implementation

- status: `ENFORCEMENT_ROLLOUT_COMPLETE`
- implementation date: `2026-07-07`
- scope: shared job enforcement plus safe wrappers for heavy research, scanner, capacity, GAP, Daily Swing backtest, fast-chart, and worker entrypoints.

## Implemented

- `assert_job_allowed` now returns machine-readable deny reasons:
  - `session_state_unknown`
  - `resource_policy_missing`
  - `paper_submit_blocked`
  - `live_job_blocked`
  - `resource_policy_denied:<job_type>:<session_state>`
  - `resource_policy_error:<ExceptionType>`
- `decide_with_market_session_policy` and `blocked_job_status` provide a shared runner-facing guard shape.
- Worker/scheduler entrypoints now check policy before opening DB sessions or running heavy work for:
  - `scan_job`
  - `self_improvement_job`
  - `discovery_job`
  - `novel_match_job`
  - `research_director_job`
  - intraday data sync/research/process-pool/candidate-scan jobs via `_run_intraday_job`
- Admin heavy-launch routes now check policy before provider, DB-heavy, or backtest work for:
  - `/scan`
  - `/research/run-discovery`
  - `/research/match-current`
  - `/research/director/run`
  - `/backtests/run`
  - `/self-improvement/run`
- Fast chart analysis now uses shared machine-readable policy reasons for unknown/missing policy states.
- Standalone heavy wrappers now fail before provider/process-pool/backtest work:
  - intraday research wave, benchmark, scouting process-pool, capacity planner
  - intraday cache warmup, universe builder, IBKR scanner candidates
  - daily OHLCV cache, GAP ledger, GAP matrix dry-run, GAP confirmatory matrix
  - Daily Swing DSS backtest/audit CLIs using `heavy_backtest`

## Safety Notes

- No live/paper mode was activated.
- No order, submit, or broker submit path was enabled.
- IBKR scanner/cache wrappers now check resource policy before connection/fetch work.
- Paper submit remains blocked by `assert_job_allowed(JobType.PAPER_SUBMIT, ...)`.

## Scope Notes

- Lab/Fox/order-adjacent submit routes were not changed beyond existing safety gates; Resource Policy still cannot authorize paper/live submit.
- Shell supervision wrappers such as `research_forever.sh` remain operator surfaces. Their child Python runners now carry direct resource policy checks where they launch heavy work.

## Validation

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_resource_policy_enforcement.py backend/tradeo/tests/test_fast_chart_engine_registry.py backend/tradeo/tests/test_intraday_worker_jobs.py backend/tradeo/tests/test_intraday_research_wave_runner.py backend/tradeo/tests/test_intraday_process_pool_benchmark_script.py backend/tradeo/tests/test_lab_daily_resource_004_red_team.py`
  - result: `83 passed, 1 warning`
- `backend/.venv/bin/python -m py_compile` over modified scripts
  - result: `pass`

## Red-Team Note

Red-team now covers API heavy-launch route guards, worker non-entry on deny, persisted deny reasons, Daily orderlessness, Lab Paper Probe separation, endpoint write safety, UI action absence, runtime artifact tracking, and secret/account-id exposure.
