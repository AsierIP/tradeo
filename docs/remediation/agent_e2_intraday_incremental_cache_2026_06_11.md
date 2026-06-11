# Agent E2 - Intraday Incremental OHLCV Cache Refresh (gap 3.1 follow-up)

Date: 2026-06-11
Branch/worktree: `main` (direct, working tree) @ base `8ba0348`.
Role: data/regime phase agent.

## Scope

Closes the "intraday incremental cache refresh" item explicitly deferred in
`agent_e_data_regime_gap_2026_06_11.md` (gap 3.1): until now only `1d`
artifacts got the overlap-verified tail append; every intraday interval
(`1m/5m/15m/30m/1h`) was cache-forever, so an intraday CSV written once never
refreshed again. No matcher/execution behavior touched.

## Sections Addressed

### 3.1 Intraday incremental cache refresh (was deferred)

- `CachedMarketDataProvider._maybe_refresh` now also refreshes intraday
  intervals using the same overlap-verified tail append as daily:
  - Gap thresholds are interval-aware: minimum gap is bar-relative
    (`market_data_incremental_intraday_min_gap_bars`, default 2 bars) so a
    5m cache refreshes on a 10-minute gap while a 1h cache waits 2 hours;
    maximum gap is wall-clock
    (`market_data_incremental_intraday_max_gap_days`, default 5 days) beyond
    which a full refetch is cheaper and safer than stitching.
  - The tail fetch period covers the gap plus a 3-day buffer so overlap bars
    survive weekends/holidays; any overlap mismatch still forces an honest
    `full_refetch_overlap_mismatch`.
  - Master switch `market_data_incremental_intraday_enabled` (default true)
    on top of the existing `market_data_incremental_enabled`; disabling it
    restores the previous cache-forever behavior exactly.
- Honest intraday bar completeness: `_bar_complete_mask` previously marked
  every intraday bar complete, including the in-progress one. It now marks an
  intraday bar complete only when `bar_start + bar_width <= now (UTC)`; naive
  timestamps are treated as UTC (IBKR intraday bars arrive tz-aware).
- Complete-bars-only persistence: the cache CSV now stores only complete bars
  (serving already filtered them, so served data is unchanged for complete
  bars). This also fixes a latent daily defect: a partial bar written mid-day
  was cemented with `bar_complete=false` and stale OHLC values, was never
  replaced by the strictly-after-last-timestamp append, and only self-healed
  via a costly overlap-mismatch full refetch. Partial bars are no longer
  persisted at all.
- Metadata/manifest honesty: `incremental_fetch_supported` now reflects
  intraday support per interval and flag state; `refresh_mode` values are
  shared with the daily path (`incremental_append`,
  `full_refetch_gap_too_large`, `full_refetch_overlap_mismatch`).

## Files Changed

- `backend/tradeo/services/data_provider.py`
- `backend/tradeo/core/config.py`
- `backend/tradeo/tests/test_data_provider.py`
- `.env.example`
- `docs/remediation/agent_e2_intraday_incremental_cache_2026_06_11.md`

## Tests Run

- `docker compose run --rm -v "$PWD/backend/tradeo:/app/tradeo:ro" backend pytest`
  → 258 passed, 3 skipped (skips are the docs-traceability tests, absent from
  the image by design). Baseline before this change collected 253 tests; the
  5 new tests cover intraday append, fresh-cache skip, gap-too-large full
  refetch, disabled-flag cache-forever, and in-progress-bar exclusion.
- `docker compose run --rm -v "$PWD/backend/tradeo:/app/tradeo:ro" backend ruff check ...`
  → clean on the three touched Python files.

## Remaining Risks / Honest Notes

- Intraday completeness assumes regular bar widths from the known interval
  map; unknown intervals (e.g. `1wk`) keep the permissive all-complete mask.
- RTH session boundaries are not modeled: the last RTH bar of the day is
  considered complete once its wall-clock width elapses, which is correct,
  but the gap measured across overnight/weekend periods is wall-clock, so the
  min-gap check effectively always passes overnight — harmless (the append is
  a no-op when no new bars exist).
- Naive intraday timestamps are interpreted as UTC for gap/completeness math;
  IBKR intraday data is tz-aware so this path is defensive only.
- The SPY regime hard-gate calibration and rediscovery items from the final
  report remain open (they require labeled outcome history, out of scope for
  this phase).
