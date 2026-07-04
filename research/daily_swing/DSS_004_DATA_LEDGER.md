# DSS-004 Data Ledger

Generated for `DSS-PB-001` on the DSS-003D pilot cache.

## Inputs

- Cache: `artifacts/runtime/daily_swing/daily_ohlcv`
- Universe: `artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv`
- Operational symbols: 50
- Benchmarks: `SPY`, `QQQ`
- Date range: 2023-07-05 to 2026-07-02
- IS end date: 2024-12-31
- OOS start date: 2025-01-01

## Gate Checks

- 50 operational symbols loaded from cache.
- `SPY` and `QQQ` loaded as benchmarks only.
- `SPY` and `QQQ` excluded from operational trades.
- Operational products are `STK`.
- No `2026-07-03` holiday bar present.
- Last valid bar date: `2026-07-02`.

## No-Lookahead Contract

- Indicators are computed through signal date `t`.
- Signal date uses close, SMA50, SMA200, 20-day benchmark return, and pullback streak available at `t`.
- Entry is theoretical next open at `t+1`.
- Exit is close after five sessions.
- No entry-day or exit-day fields are used to decide the signal.

Artifact: `artifacts/runtime/daily_swing/dss_004_data_ledger_summary.json`.
