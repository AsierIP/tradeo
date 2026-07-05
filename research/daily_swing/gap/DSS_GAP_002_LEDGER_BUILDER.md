# DSS-GAP-002 Ledger Builder

Generated: 2026-07-05T14:13:53Z

## Implementation

Added a cache-only GAP-002 ledger builder:

- `backend/tradeo/modules/daily_swing/gap_event_ledger.py`
- `scripts/build_daily_gap_event_ledger.py`
- `backend/tradeo/tests/test_daily_gap_event_ledger.py`

The script accepts:

- `--cache-dir`
- `--universe`
- `--output-dir`
- `--start-date`
- `--end-date`
- `--min-history-days`
- `--cache-only`
- `--no-ibkr`

The script refuses:

- execution without `--cache-only`;
- execution without `--no-ibkr`;
- orders;
- previews;
- signals;
- execute mode.

## Runtime Status

The requested cache path was missing, so no runtime ledger CSV was generated. The runner returned exit code `3` with decision:

`GAP_EVENT_LEDGER_BLOCKED_CACHE_MISSING`

When the cache and universe are available, the intended local, non-versioned outputs are:

- `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger_summary.json`

## Field Availability

The builder marks fields as:

- `known_at_open_fields`
- `known_after_close_fields`
- `outcome_only_fields`

Same-day outcomes are present only as descriptive audit fields and are not marked as known at open.
