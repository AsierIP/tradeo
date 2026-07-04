# DSS-004 Final Report

Final decision: `DSS_PB_001_RESEARCH_FAIL`

## A. Executive Summary

DSS-004 ran a real cache-only backtest for `DSS-PB-001 Pullback in Uptrend Long` on the DSS-003D pilot cache. The pattern has positive full-sample net x2 expectancy, but it fails the Director's OOS hurdle: OOS net x2 expectancy is negative and OOS net x2 profit factor is below 1.0. Do not advance to DSS-005.

## B. Execution

- Path: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`
- Branch: `feature/daily-swing-paper-probe-001`
- Cache: `artifacts/runtime/daily_swing/daily_ohlcv`
- Universe: `artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv`
- Symbols: 50 operational stocks + `SPY`/`QQQ` benchmarks
- Dates: 2023-07-05 to 2026-07-02

## C. Pattern Definition

- Market regime: `SPY close > SMA200 OR SPY return20d > 0`
- Trend: `close > SMA50 AND (close > SMA200 OR SMA50 > SMA200)`
- Pullback: 2 to 4 consecutive down closes
- Entry: next open after signal
- Exit: five-session time stop at close
- Costs: x1=10 bps, x2=20 bps, x3=30 bps round trip

## D. Results

- Trades total / IS / OOS: 925 / 368 / 557
- Symbols total / IS / OOS: 50 / 47 / 50
- Gross expectancy / PF: 0.5522% / 1.1947
- Net x1 expectancy / PF: 0.4522% / 1.1567
- Net x2 expectancy / PF: 0.3522% / 1.1199
- Net x3 expectancy / PF: 0.2522% / 1.0844
- IS net x2 expectancy / PF: 0.9721% / 1.4340
- OOS net x2 expectancy / PF: -0.0573% / 0.9831
- Worst streak: 18
- Max closed-trade cumulative drawdown: 360.12 percentage points

## E. Concentration and Robustness

- Top 1 symbol positive contribution: 19.06%
- Top 3 symbols positive contribution: 39.06%
- Top 5 trades positive contribution: 9.40%
- Lookahead, leakage, duplicate, and holiday audits passed.
- Entry next close remains positive but does not fix OOS.
- Placebo +5 turns negative; placebo +1/+2 remaining positive is a warning, not validation.

## F. Candidate Count

- Research-only candidate signals for 2026-07-06: 4
- No preview file, paper execution, order, or signal publication was generated.

## G. Safety Confirmation

Confirmed: no orders, no paper execution, no live, no cron, no `.env` modification, no merge, no PR, no operational signal generation.

## H. Decision

`DSS_PB_001_RESEARCH_FAIL`

Reason: OOS net x2 expectancy is negative and OOS net x2 PF is 0.9831, below the minimum research hurdle.

## I. Recommended Next Phase

Do not run DSS-005 for this pattern. Recommended Director options:

1. Reject `DSS-PB-001` as currently specified and test reserve pattern `DSS-BO-001` in a separate authorized task.
2. Or authorize a narrow diagnostic task to inspect why OOS degraded, without optimization or paper preview.
