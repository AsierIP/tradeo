# DSS-003E-R Mini Batch

Decision: MINI_BATCH_OK_READY_FOR_RESEARCH_RESUME

Mini universe:
- 8 operational stocks: AAON, AEO, ALGM, APPF, AX, BROS, AAPL, MSFT.
- 2 benchmark-only ETFs: SPY, QQQ.

Cache run:
- Source: IBKR read-only, paper port 4002.
- Duration: 3Y Daily.
- `max_new_fetches=10`.
- `max_consecutive_timeouts=2`.
- `retry_count=1`.
- `request_timeout=25`.
- Result: `CACHE_WRITTEN`.
- Fetched: 10.
- Failed: 0.
- Skipped: 0.

Quality gate:
- `data_gate=PASS`.
- `operational_ready=8`.
- `benchmark_ready=2`.
- `false_bar_2026_07_03_present=false`.
- `last_valid_bar_date=2026-07-02`.

Artifacts:
- `artifacts/runtime/daily_swing/dss_003e_r_mini_batch_manifest.json`
- `artifacts/runtime/daily_swing/dss_003e_r_mini_batch_quality_report.csv`
- `artifacts/runtime/daily_swing/dss_003e_r_mini_batch_quality_summary.json`

Safety: this was a mini batch only. It did not run research-150, DSS-004E, backtests, signals, preview, paper execution, or live execution.
