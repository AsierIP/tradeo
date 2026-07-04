# DSS-004G-A Validation Protocol

## Purpose

This protocol defines how `DSS-CW-001` should be tested later without turning the known +1/+2/+5 timing behavior into retrospective optimization. No test is executed in DSS-004G-A.

## Split Policy

- Preserve the current Daily research split for comparability:
  - IS through `2024-12-31`.
  - OOS from `2025-01-01`.
- If any timing/window variant is selected, it must be selected only on IS or in a nested calibration layer.
- OOS may be used once for final evaluation of a frozen specification.

## Evaluation Universe

- Primary evaluation: research-150 operational equities.
- Benchmarks `SPY` and `QQQ` only support regime/benchmark logic.
- Subuniverse checks may be run only as robustness diagnostics, not as a selection mechanism unless covered by multiple-testing correction.

## Required Comparisons

- Base `DSS-CW-001` frozen specification.
- `DSS-CO-001` canonical reference.
- Delayed offsets as adversarial/placebo controls, not as alternatives optimized for adoption.
- Trend-only baseline.
- Random-matched baseline.
- Vol-high-only baseline.
- Contraction-only baseline if implementation is clean and pre-declared.

## Statistical Robustness

Future DSS-004G-B should compute:

- Bootstrap by symbol.
- Bootstrap by symbol-month.
- Episode-level bootstrap if implementation is available.
- Concentration audit: top3 contribution and top5 trade share.
- Effective sample audit: raw signals, episodes, trades, and OOS effective counts.
- Last-12-months performance.
- Cost stress x3.

## FDR/WRC/SPA-Light

Before any live or paper approval, the repo should either reuse an existing implementation or add a small documented research module for:

- FDR correction over declared variants.
- White's Reality Check or SPA-light over declared variants and baselines.
- Clear labeling of exploratory vs confirmatory results.

If reusable implementation is not found, a separate technical task should build and test it before any candidate can become `paper_probe_candidate`.

## Minimum Decision Criteria

For `DSS-CW-001` to become `SPEC_READY_FOR_NEXT_REVIEW` after a future research-only backtest, all of the following should hold or be explicitly downgraded to warning:

- OOS net x2 expectancy > 0.
- OOS PF x2 > 1.20.
- MAX2 PF x2 > 1.15.
- Cost x3 does not destroy the edge.
- Last 12 months net x2 expectancy is not negative.
- Effective sample warning is absent or explicitly accepted by Direction.
- Symbol bootstrap p05 is not materially negative, or warning remains.
- Placebos and delayed adversarial offsets do not dominate the frozen base.
- Top3 and top5 concentration do not explain the majority of the result.
- No lookahead, leakage, ETF/ETP/fund contamination, fake bar contamination, or benchmark trade leakage.

## Rejection Criteria

Reject or keep in research warning if:

- The base result only works after choosing a delayed offset post hoc.
- Placebo/adversarial timing dominates the base.
- OOS PF x2 falls below 1.15 under portfolio-like constraints.
- Symbol bootstrap p05 remains negative and Direction does not explicitly accept the warning.
- FDR/WRC/SPA-light flags the result as indistinguishable from the declared alternative set.

## Output Required For Future DSS-004G-B

- Final report.
- Decision JSON.
- Backtest config JSON.
- Metrics JSON and CSV by policy, symbol, period, and episode.
- Bias/placebo/adversarial JSON.
- Guard JSON.
- Explicit safety statement: no orders, no paper, no live, no preview, no operational signals.
