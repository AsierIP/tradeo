# DSS-GAP-004 Input Matrix Gate

Decision: INPUT_MATRIX_GATE_PASS

Scope:
- Ledger runtime: `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv`.
- Matrix: `research/daily_swing/gap/dss_gap_003_backtest_matrix.json`.
- Validation script: `scripts/validate_daily_gap_backtest_matrix.py`.

Checks:
- Ledger exists locally and is under ignored runtime artifacts.
- Ledger range is 2023-07-05 through 2026-07-02, covering the requested IS/OOS split.
- Matrix validation passed with 92 rows, 40 pre-registered candidate rows, 8 baseline rows, and 16 placebo rows.
- No duplicate `test_id` values were found by matrix validation.
- All matrix execution gates are false: `execution_allowed`, `signal_output_allowed`, `preview_allowed`, `paper_allowed`, and `live_allowed`.
- Families present: GAP_CONTINUATION_SAME_DAY, GAP_REVERSAL_SAME_DAY, GAP_CONTINUATION_NEXT_DAY, GAP_REVERSAL_NEXT_DAY.
- Portfolio policies present: ALL_EVENTS_RESEARCH_ONLY, MAX_2_NEW_TRADES_PER_DAY, ONE_ACTIVE_PER_SYMBOL.

Result:
- INPUT_MATRIX_GATE_PASS.
- Proceeded to cache-only dry-run.
