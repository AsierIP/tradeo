# DSS-GAP-004 Dry-run Engine

Decision: DRY_RUN_METRICS_COMPLETE

Implemented:
- Module: `backend/tradeo/modules/daily_swing/gap_matrix_dry_run.py`.
- CLI: `scripts/run_daily_gap_matrix_dry_run.py`.
- Tests: `backend/tradeo/tests/test_daily_gap_matrix_dry_run.py`.

CLI guardrails:
- Requires `--cache-only`.
- Requires `--no-ibkr`.
- Requires `--no-signals`, `--no-preview`, and `--no-orders`.
- Refuses hidden positive execution flags for IBKR, signals, preview, and orders.

Runtime outputs:
- `artifacts/runtime/daily_swing/gap/dss_gap_004_results_by_test.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_004_results_by_policy.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_004_results_by_family.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_004_dry_run_summary.json`

Versioned sanitized summaries:
- `research/daily_swing/gap/dss_gap_004_results_summary_by_family.csv`
- `research/daily_swing/gap/dss_gap_004_results_summary_by_policy.csv`
- `research/daily_swing/gap/dss_gap_004_results_summary_top_observations.csv`

Execution:
- Matrix rows executed: 92.
- Ledger rows read: 114304.
- Families: same-day continuation/reversal and next-day continuation/reversal.
- Policies: all-events research-only, max-2-new-trades-per-day, one-active-per-symbol.
- Candidate approval: false.
- Best threshold selected: false.
