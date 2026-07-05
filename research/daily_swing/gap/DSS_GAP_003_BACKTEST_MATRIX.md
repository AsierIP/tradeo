# DSS-GAP-003 Backtest Matrix

Task: T-DAILY-GAP-003
Status: matrix-only; no execution.
Decision: GAP_BACKTEST_MATRIX_READY_FOR_CACHE_ONLY_DRY_RUN

## Scope

This file pre-registers the closed cache-only matrix for a future GAP-004 dry run. It
does not execute a backtest, infer edge, select a best threshold, emit signals, create
preview output, access IBKR, download data, or approve paper/live trading.

Machine-readable artifacts:

- `dss_gap_003_backtest_matrix.csv`
- `dss_gap_003_backtest_matrix.json`

## Matrix Summary

- Total rows: 92.
- Candidate tests: 40 with cap 40.
- Baseline/placebo/design rows: 52.

Families:

- `GAP_CONTINUATION_SAME_DAY`: 23 rows.
- `GAP_REVERSAL_SAME_DAY`: 23 rows.
- `GAP_CONTINUATION_NEXT_DAY`: 23 rows.
- `GAP_REVERSAL_NEXT_DAY`: 23 rows.

Portfolio policies:

- `ALL_EVENTS_RESEARCH_ONLY`.
- `MAX_2_NEW_TRADES_PER_DAY`.
- `ONE_ACTIVE_PER_SYMBOL`.

Baseline/placebo groups:

- `DESIGN_LOCKED_FILTER_OR_POLICY`.
- `DELAYED_ENTRY`.
- `EARNINGS_SENSITIVITY`.
- `MATCHED_NON_GAP`.
- `RANDOM_MATCHED`.
- `SIGN_INVERTED_GAP`.
- `THRESHOLD_PERTURBATION`.

## Pre-Registration Rules

- Same-day families decide at `open_t` and may not use `high_t`, `low_t`, `close_t`,
  `volume_t`, `gap_fill_ratio`, or outcome fields for entry decisions.
- Next-day families decide after `close_t` and may use completed day-t OHLCV before
  `open_t_plus_1`.
- SPY/QQQ are benchmark/regime inputs only.
- Thresholds are fixed before GAP-004 and cannot be optimized from results.
- All execution, signal, preview, paper, and live flags are hard-coded false.

## Future Research-Pass Contract

Future GAP-004 can only report research evidence. It cannot approve candidates unless a
separate Director task explicitly authorizes a later promotion gate.
