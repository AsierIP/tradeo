# DSS-003 Data Source Audit

Best existing path: reuse `IBKRHistoricalDataProvider.fetch_ohlcv()` from `backend/tradeo/services/ibkr_data_provider.py`.

Findings:
- It already qualifies `Stock(symbol, SMART, USD)` and requests historical bars through IBKR.
- It supports `1d` via `_bar_size_from_interval`.
- It uses `TRADEO_MARKET_DATA_WHAT_TO_SHOW`, default `ADJUSTED_LAST`.
- It has no reusable Daily cache writer, manifest, resume, or quality gate.

Decision: add `scripts/cache_daily_ohlcv.py` and `scripts/check_daily_ohlcv_quality.py` as read-only Daily cache tooling, without changing intraday infrastructure.
