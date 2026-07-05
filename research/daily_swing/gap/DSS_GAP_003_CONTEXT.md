# DSS-GAP-003 Context

Task: T-DAILY-GAP-003
Status: context-only.

## Sources Read

- `DSS_GAP_001_PREREGISTERED_SPEC.md`
- `DSS_GAP_001_BIAS_ADVERSARIAL_PROTOCOL.md`
- `DSS_GAP_001_FINAL_REPORT.md`
- `DSS_GAP_002A_FINAL_REPORT.md`
- `DSS_GAP_002A_DECISION.json`
- `DSS_GAP_002A_RERUN_LEDGER.json`
- `dss_gap_002_gap_distribution_summary.csv`
- `dss_gap_002_events_by_symbol_summary.csv`
- `dss_gap_002_events_by_period_summary.csv`

## Accepted Prior State

- GAP-001 defined four families before testing: same-day continuation, same-day
  reversal, next-day continuation, and next-day reversal.
- GAP-002A restored the local cache-only runtime and produced a real event ledger
  with 114304 rows, 152 symbols, 150 operational symbols, 54942 ready events, and
  date range 2023-07-05 through 2026-07-02.
- GAP-002A reported `NO_LOOKAHEAD_PASS` and did not infer edge, select thresholds,
  emit signals, create preview output, use IBKR, download data, or run a backtest.

## Explicit Non-Goals

- GAP-003 does not rescue PB, BO, CO, or CW.
- GAP-003 does not create DSS-005.
- GAP-003 does not execute the matrix.
- GAP-003 does not calculate PnL, expectancy, PF, or edge.
- GAP-003 does not generate signals, preview, paper, live, orders, IBKR calls, data
  downloads, cron jobs, or main-branch changes.

## Context Decision

GAP-003 may proceed as a pre-registered matrix and validation scaffold only.
