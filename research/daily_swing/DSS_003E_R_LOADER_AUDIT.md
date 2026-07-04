# DSS-003E-R Loader Audit

Decision: LOADER_PATCH_APPLIED

Before this task, `scripts/cache_daily_ohlcv.py` exposed only coarse `--resume`, `--sleep`, `--limit`, and `--force` controls. The underlying loader wrote a manifest, but failures lacked structured `error_type`, attempts, quarantine, timeout caps, and benchmark-specific stop rules.

Findings:
- Request timeout existed in `IBKRHistoricalDataProvider.fetch_ohlcv()` only as a hard-coded historical request default.
- The loader had no CLI `--request-timeout`, `--retry-count`, `--retry-backoff-seconds`, `--max-new-fetches`, or `--max-consecutive-timeouts`.
- Per-symbol failure quarantine was absent.
- Resume skipped files by path existence only; now it requires a readable cache file with required OHLCV columns.
- DSS-003E showed `skipped=0` because it used `artifacts/runtime/daily_swing/daily_ohlcv_research`, while the pilot cache lives in `artifacts/runtime/daily_swing/daily_ohlcv`.

Patch summary:
- Added timeout/retry/backoff/max-fetch/max-timeout CLI controls.
- Added structured symbol manifest fields: `attempts`, `error_type`, `error_message`, `last_attempt_at`, `quarantine`, and `cache_file`.
- Added benchmark failure stop logic.
- Added tests for timeout recording, timeout caps, benchmark stop, resume skip, quarantine, and max-new-fetches.

Safety: no orders, no paper, no live, no backtest, no signals, no preview.
