# DSS-GAP-002A Rerun Ledger

Decision: GAP_LEDGER_RERUN_READY.

Command:

`python /app/scripts/build_daily_gap_event_ledger.py --cache-only --no-ibkr --cache-dir artifacts/runtime/daily_swing/daily_ohlcv_research --universe artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv --output-dir artifacts/runtime/daily_swing/gap --research-output-dir research/daily_swing/gap`

Executed inside the backend Docker image with the selected cache mounted read-only.

Ledger result:

- Local ledger path: `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv`
- Ledger versioned: no.
- Summary path: `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger_summary.json`
- Rows: 114304.
- Symbols total: 152.
- Operational symbols: 150.
- Date start: 2023-07-05.
- Date end: 2026-07-02.
- Events ready: 54942.
- No-lookahead status: NO_LOOKAHEAD_PASS.

Coverage summaries versioned:

- `research/daily_swing/gap/dss_gap_002_gap_distribution_summary.csv`
- `research/daily_swing/gap/dss_gap_002_events_by_symbol_summary.csv`
- `research/daily_swing/gap/dss_gap_002_events_by_period_summary.csv`

Event quality counts:

- GAP_EVENT_READY: 54942.
- GAP_EVENT_TOO_SMALL: 54809.
- GAP_EVENT_INSUFFICIENT_HISTORY: 3000.
- GAP_EVENT_BENCHMARK_ONLY: 1504.
- GAP_EVENT_SPLIT_ADJUSTMENT_SUSPECT: 49.

No edge, strategy PnL, best threshold, continuation/reversal selection, signals, preview, paper, live, orders, IBKR, downloads, cron, or `.env` changes were produced.
