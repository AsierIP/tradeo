# DSS-003 Cache Loader

Loader: `scripts/cache_daily_ohlcv.py`

Cache status: BLOCKED_IBKR_READONLY
Fetched: 0
Skipped: 0
Failed: 12
Manifest: `artifacts/runtime/daily_swing/dss_003_daily_cache_manifest.json`

The loader requires explicit `--read-only`. It writes one CSV per symbol and a manifest. It is idempotent with `--resume` and refuses unsupported sources.

Error: [Errno -2] Name or service not known
