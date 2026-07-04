# DSS-004 Backtest Engine

Implemented cache-only backtest runner:

- `backend/tradeo/modules/daily_swing/dss_004.py`
- `scripts/backtest_daily_swing_dss_pb_001.py`

## DSS-PB-001 Definition

- Pattern: Pullback in Uptrend Long.
- Market regime: `SPY close > SMA200 OR SPY return20d > 0`; QQQ fallback is available if SPY lacks enough history.
- Symbol trend: `close > SMA50 AND (close > SMA200 OR SMA50 > SMA200)`.
- Pullback: 2 to 4 consecutive down closes.
- Entry: next open after signal.
- Exit: five-session time stop at close.
- Costs: round-trip x1=10 bps, x2=20 bps, x3=30 bps.
- Metrics are percentage based. R metrics remain pending because no robust stop/risk unit was defined.

## Safety Rejections

The runner rejects execution if cache files are missing, SPY/QQQ are missing, a `2026-07-03` bar appears, operational ETF/fund rows are present, or the no-lookahead contract cannot be maintained.

## Outputs

- `artifacts/runtime/daily_swing/dss_pb_001_trades.csv`
- `artifacts/runtime/daily_swing/dss_pb_001_daily_equity.csv`
- `artifacts/runtime/daily_swing/dss_pb_001_backtest_config.json`
