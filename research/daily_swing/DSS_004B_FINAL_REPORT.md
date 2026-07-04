# DSS-004B Final Report

Final decision: `DSS_BO_001_RESEARCH_WARNING`

## A. Executive Summary

DSS-004B ran a real cache-only backtest for `DSS-BO-001 Volatility Contraction Breakout Long` on the DSS-003D pilot cache. OOS results are strong enough to stay in consideration, but robustness is not clean because placebo signal shifts also remain positive. Do not declare paper-ready.

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
- Volatility contraction: `ATR14_pct(t-1) <= rolling 120-day percentile 40 through t-1`
- Breakout: `close_t > prior high20`
- Entry: next open after signal
- Exit: ten-session time stop at close
- Costs: x1=10 bps, x2=20 bps, x3=30 bps round trip

## D. Results

- Trades total / IS / OOS: 350 / 124 / 226
- Symbols total / IS / OOS: 50 / 44 / 49
- Gross expectancy / PF: 1.5829% / 1.4599
- Net x2 full-sample expectancy / PF: 1.3829% / 1.3917
- IS net x2 expectancy / PF: 0.4961% / 1.1373
- OOS net x2 expectancy / PF: 1.8694% / 1.5363
- Max closed-trade cumulative drawdown: 185.54 percentage points
- Worst streak: 8

## E. Robustness and Safety

- Top 1 symbol positive contribution: 13.35%
- Top 3 symbols positive contribution: 30.73%
- Top 5 trades positive contribution: 10.95%
- Lookahead, leakage, duplicate, and holiday audits passed.
- Placebo +1/+2/+5 remain positive, so the decision is warning rather than pass.
- Research-only candidate count for 2026-07-06: 2.

Confirmed: no orders, no paper execution, no live, no cron, no `.env` modification, no merge, no PR, no operational signal generation.

## F. Recommended Next Step

Either authorize a narrow robustness/autopsy task for DSS-BO-001, or expand to the research-150 cache before repeating. Do not generate DSS-005 preview from this task alone.
