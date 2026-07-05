# DSS-GAP-002A Runtime Restore

Decision: RUNTIME_RESTORE_READY.

Restore method: local symlink, not versioned.

Runtime links created in `/tmp/tradeo-main-004k-clean`:

- `artifacts/runtime/daily_swing/daily_ohlcv_research` -> selected research OHLCV cache.
- `artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv` -> selected research universe.
- `artifacts/runtime/daily_swing/gap` -> local runtime output directory.

Git hygiene:

- `artifacts/runtime` remains untracked runtime data.
- The full event ledger remains under `artifacts/runtime/daily_swing/gap` and is not versioned.
- Only sanitized summaries and reports under `research/daily_swing/gap` are versioned.

Security:

No IBKR, no downloads, no backtest, no signals, no preview, no orders, no paper, no live, no cron, no `.env` modification.

