# DSS-004C Final Report

Final decision: `DSS_BO_001_TIMING_WINDOW_WARNING`

## A. Executive Summary

DSS-004C completed the specificity autopsy for `DSS-BO-001` without changing the base specification. The pattern remains strong and stable, but it is not a clean specificity pass. The best interpretation is a post-breakout / volatility-compression timing window, not a one-day breakout trigger.

Do not generate DSS-005 yet. The recommended next step is `DSS-003E` research-150 confirmation before any paper-probe preview.

## B. Execution

- Path: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`
- Branch: `feature/daily-swing-paper-probe-001`
- Cache: `artifacts/runtime/daily_swing/daily_ohlcv`
- Universe: `artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv`
- Data: 50 operational stocks plus `SPY`/`QQQ` benchmarks
- Dates: 2023-07-05 to 2026-07-02

## C. Partial Decisions

- Placebo OOS audit: `PLACEBO_TIMING_WINDOW_WARNING`
- Matched baseline audit: `BASELINE_WARNING`
- Return decomposition: `TIMING_PASS`
- Stability audit: `STABILITY_PASS`

## D. Key Evidence

- Base OOS net x2 expectancy / PF: 1.8694% / 1.5363 over 226 trades and 49 symbols.
- Placebo +1 remains very close: 1.8339% / 1.5331.
- Placebo +5 also remains strong: 1.6794% / 1.4919.
- Contraction-only baseline is close: 1.6253% / 1.4344.
- Trend-only and breakout-only do not explain the result.
- Random matched fails: -0.7872% / 0.8187.
- Return appears after entry, especially days 3-10, not only in the overnight gap.
- Excluding top 3 symbols still leaves positive OOS expectancy 0.9274% and PF 1.2569.

## E. Safety

Confirmed: no orders, no paper execution, no live, no cron, no `.env` modification, no merge, no PR, no operational preview, no operational signals, no data download.

## F. Recommendation

Do not reject DSS-BO-001, but do not call it paper-ready. Promote it to `NEEDS_RESEARCH_150_CONFIRMATION`.

Recommended next task: `DSS-003E` cache research 150 and rerun DSS-004B/004C unchanged. If the timing-window behavior survives broader data, Director can decide whether DSS-005 preview paper-probe is justified.
