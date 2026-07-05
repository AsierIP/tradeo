# DSS-GAP-002 Coverage / Distribution

Generated: 2026-07-05T14:13:53Z

## Status

Coverage and distribution on real cache data are blocked:

`GAP_EVENT_LEDGER_BLOCKED_CACHE_MISSING`

No runtime ledger rows were available, so no symbol/date/event distribution was inferred.

## Implemented Outputs

When local cache is present, the builder can produce versionable, sanitized summary CSVs:

- `research/daily_swing/gap/dss_gap_002_gap_distribution_summary.csv`
- `research/daily_swing/gap/dss_gap_002_events_by_symbol_summary.csv`
- `research/daily_swing/gap/dss_gap_002_events_by_period_summary.csv`

The summaries are inventory-only. They do not report a best threshold, best strategy, edge, PnL, continuation selection, reversal selection, paper readiness, or shadow readiness.
