# DSS GAP-006 Evidence Reader

Generated: 2026-07-05T16:30:00Z

## Inputs Read

- `DSS_GAP_005_FINAL_REPORT.md`
- `DSS_GAP_005_DECISION.json`
- `dss_gap_005_triage_matrix.csv`
- `dss_gap_005_triage_matrix.json`
- `DSS_GAP_005_RESULTS_INTEGRITY.md`
- `DSS_GAP_005_BASELINE_PLACEBO_OPEN_REALISM.md`

## Findings

GAP-005 ended with `GAP_FORENSIC_OBSERVATIONS_READY_FOR_CONFIRMATION_DESIGN`. It explicitly did not approve any candidate, paper candidate, shadow candidate, live candidate, best threshold, signal, preview, order, or IBKR use.

The only observations allowed into GAP-006 are:

| test_id | status | events_OOS | symbols_OOS | pf_x2 | expectancy_x2 | x3 | 25bps | 50bps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL` | observation only | 3495 | 148 | 1.149045 | 0.00232996 | 0.00132996 | 0.00182996 | -0.00067004 |
| `GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0` | observation only | 7362 | 150 | 1.164642 | 0.00181005 | 0.00081005 | 0.00131005 | -0.00118995 |

Both observations carry the same critical warnings:

- PF x2 is below the preferred 1.2 threshold.
- Open slippage 50 bps is negative.
- Same-day open realism remains unresolved.
- They can only feed a confirmatory design; they are not candidates.

## Confirmation Boundary

GAP-006 may only pre-register a future GAP-007 protocol. It must not execute a backtest, recalculate edge, create signals, create preview output, use IBKR, touch main, or approve paper/shadow/live readiness.
