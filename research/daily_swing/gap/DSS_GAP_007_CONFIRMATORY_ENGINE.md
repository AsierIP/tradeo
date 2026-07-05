# DSS-GAP-007 Confirmatory Engine

Decision: `GAP_CONFIRMATION_FAIL_OPEN_SLIPPAGE`.

Implementation:

- Added `backend/tradeo/modules/daily_swing/gap_confirmatory_run.py`.
- Added `scripts/run_daily_gap_confirmatory_matrix.py`.
- Runtime outputs:
  - `artifacts/runtime/daily_swing/gap/dss_gap_007_results_by_test.csv`
  - `artifacts/runtime/daily_swing/gap/dss_gap_007_results_summary.json`
  - `artifacts/runtime/daily_swing/gap/dss_gap_007_bootstrap.csv`
  - `artifacts/runtime/daily_swing/gap/dss_gap_007_fdr_wrc_spa_light.json`
- Versioned research summaries:
  - `research/daily_swing/gap/dss_gap_007_results_summary_by_test.csv`
  - `research/daily_swing/gap/dss_gap_007_bootstrap_summary.csv`
  - `research/daily_swing/gap/DSS_GAP_007_DECISION.json`

Execution summary:

- Matrix rows executed: 12.
- Ledger rows read: 114304.
- Confirmation targets: 6.
- No candidate approval emitted.
- No signals, preview, orders, paper/live, IBKR, downloads or cron paths are available from the runner.

Target results:

| test_id | policy | events_OOS | symbols_OOS | expectancy_oos_x2 | pf_oos_x2 | slippage_50bps | slippage_75bps |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GAP006_OBS1_REFERENCE_ALL | ALL_EVENTS_RESEARCH_ONLY | 3495 | 148 | 0.00356055 | 1.237430 | 0.00056055 | -0.00193945 |
| GAP006_OBS1_ONE_ACTIVE | ONE_ACTIVE_PER_SYMBOL | 3495 | 148 | 0.00356055 | 1.237430 | 0.00056055 | -0.00193945 |
| GAP006_OBS1_MAX2 | MAX_2_NEW_TRADES_PER_DAY | 686 | 107 | -0.00209933 | 0.878991 | -0.00509933 | -0.00759933 |
| GAP006_OBS2_REFERENCE_ALL | ALL_EVENTS_RESEARCH_ONLY | 7362 | 150 | 0.00172545 | 1.145552 | -0.00127455 | -0.00377455 |
| GAP006_OBS2_ONE_ACTIVE | ONE_ACTIVE_PER_SYMBOL | 7362 | 150 | 0.00172545 | 1.145552 | -0.00127455 | -0.00377455 |
| GAP006_OBS2_MAX2 | MAX_2_NEW_TRADES_PER_DAY | 250 | 21 | -0.00211581 | 0.846896 | -0.00511581 | -0.00761581 |

OBS2 fails the 50 bps open slippage requirement under reference and one-active policy. MAX2 fails both observations out-of-sample. OBS1 reference/one-active survives 50 bps, but fails 75 bps, so it is not robust enough to override the open-realism gate.
