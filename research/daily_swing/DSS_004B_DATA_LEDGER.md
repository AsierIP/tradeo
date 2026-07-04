# DSS-004B Data Ledger

Decision: `DATA_LEDGER_PASS`

- Cache: `artifacts/runtime/daily_swing/daily_ohlcv`
- Universe: `artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv`
- Operational symbols: 50 stocks
- Benchmarks: `SPY`, `QQQ`
- Last valid bar date: `2026-07-02`
- False `2026-07-03` bar present: `false`

No-lookahead controls:

- Regime uses benchmark data available at signal date `t`.
- ATR14 contraction uses `ATR14_pct(t-1)`.
- Contraction threshold uses the rolling 120-day 40th percentile through `t-1`.
- Breakout uses only prior highs from `t-20` through `t-1`.
- Signal is on `t`; theoretical entry is on `t+1`.

