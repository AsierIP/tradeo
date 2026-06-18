# Internal Auditor Agent Review

- Audit ID: `TRADEO-AUDIT-20260617-213620_daily_internal`
- Status: `blocked`
- Priority: `P0`
- Promotion decision: `stay_in_research`

## Top blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.
- duplicate_group_id repeats exceed gate: 139/5606 rows (2.48%).
- 2995 experiment rows have nested_discovery_replay not implemented/passed.
- experiment rows report active blockers: EXP_PATTERN_000490_RR_1_5, EXP_PATTERN_000490_RR_2, EXP_PATTERN_000490_RR_2_5, EXP_PATTERN_000490_RR_3, EXP_PATTERN_000490_RR_4, EXP_PATTERN_000490_RR_5, EXP_PATTERN_000560_RR_1_5, EXP_PATTERN_000560_RR_2, EXP_PATTERN_000560_RR_2_5, EXP_PATTERN_000560_RR_3 (+182 more)

## Required next actions

- Keep all patterns in research/watchlist until paper trades are exported.
- Ingest IB Paper fills with commissions, spread and slippage before promotion.