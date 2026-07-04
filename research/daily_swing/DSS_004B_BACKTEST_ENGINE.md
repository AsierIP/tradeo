# DSS-004B Backtest Engine

Decision: `BACKTEST_ENGINE_PASS`

Implemented cache-only DSS-BO-001 in:

- `backend/tradeo/modules/daily_swing/dss_004b.py`
- `scripts/backtest_daily_swing_dss_bo_001.py`

The script accepts `--cache-dir`, `--universe`, `--start-date`, `--end-date`, `--is-end-date`, `--oos-start-date`, `--cost-mode`, and `--output-dir`.

Reject conditions include missing cache files, missing benchmark files, operational non-stock products, operational `SPY`/`QQQ`, invalid OHLCV rows, and any `2026-07-03` bar.

Outputs:

- `artifacts/runtime/daily_swing/dss_bo_001_trades.csv`
- `artifacts/runtime/daily_swing/dss_bo_001_daily_equity.csv`
- `artifacts/runtime/daily_swing/dss_bo_001_backtest_config.json`

