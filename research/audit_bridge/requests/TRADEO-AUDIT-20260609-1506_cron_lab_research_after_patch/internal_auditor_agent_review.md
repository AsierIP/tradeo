# Internal Auditor Agent Review

- Audit ID: `TRADEO-AUDIT-20260609-1506_cron_lab_research_after_patch`
- Status: `blocked`
- Priority: `P0`
- Promotion decision: `stay_in_research`

## Top blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.
- promoted statuses require linked paper trades; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366
- promoted statuses require at least 30 IB Paper fills; package has 0.
- research R metrics are populated in operational metric columns while trade_count is zero; offenders: PATTERN_000200, PATTERN_000466, PATTERN_000410, PATTERN_000617, PATTERN_000103, PATTERN_000349, PATTERN_000223, PATTERN_000258, PATTERN_000237, PATTERN_000490 (+110 more)
- duplicate_group_id repeats exceed gate: 202/1471 rows (13.73%).
- 202 event rows are not verified independent samples.
- 202 event rows have pending/unknown independence labels.
- independent_sample_count is not reconstructable from exported event rows for 120 patterns.
- no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.

## Required next actions

- Keep all patterns in research/watchlist until paper trades are exported.
- Ingest IB Paper fills with commissions, spread and slippage before promotion.
- Add explicit OOS/walk-forward boundaries and metrics.