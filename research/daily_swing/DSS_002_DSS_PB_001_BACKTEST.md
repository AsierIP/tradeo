# DSS-002 DSS-PB-001 Backtest

RESEARCH_GATE=INSUFFICIENT_DATA

Pattern: DSS-PB-001 Pullback in Uptrend Long.

The run did not execute a real historical backtest because the local branch has no reusable Daily OHLCV cache for the seed universe. I did not use the deterministic AAPL/COST scaffold preview as evidence.

Required metrics are recorded in `artifacts/runtime/daily_swing/dss_pb_001_metrics.json` with null performance values and `real_backtest=false`.

Key outcome:
- trades total: 0
- symbols total: 40
- IS expectancy: not_available
- OOS expectancy: not_available
- IS PF: not_available
- OOS PF: not_available
- cost x1/x2/x3: not_available
- candidate signals for Monday 2026-07-06: 0 real signals

Decision: no paper probe promotion from research evidence.
