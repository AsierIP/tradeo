# Internal Auditor Agent Review

- Audit ID: `TRADEO-AUDIT-20260608-061533_daily_internal`
- Status: `blocked`
- Priority: `P0`
- Promotion decision: `stay_in_research`

## Top blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.
- promoted statuses require linked paper trades/fills; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366
- duplicate_group_id repeats exceed gate: 341/5480 rows (6.22%).
- 500 event rows are not verified independent samples.
- 500 event rows have pending/unknown independence labels.
- independent_sample_count is not reconstructable from exported event rows for 465 patterns.
- market_regime is not persisted; cross-regime robustness cannot be audited.
- sector is not persisted; cross-sector concentration cannot be audited.
- no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.

## Required next actions

- Keep all patterns in research/watchlist until paper trades are exported.
- Ingest IB Paper fills with commissions, spread and slippage before promotion.
- Add explicit OOS/walk-forward boundaries and metrics.
- Persist market regime and sector, then regenerate metrics_by_regime.csv.