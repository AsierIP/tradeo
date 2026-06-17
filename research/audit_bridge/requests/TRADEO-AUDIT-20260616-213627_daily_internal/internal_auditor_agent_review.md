# Internal Auditor Agent Review

- Audit ID: `TRADEO-AUDIT-20260616-213627_daily_internal`
- Status: `blocked`
- Priority: `P0`
- Promotion decision: `stay_in_research`

## Top blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.
- promoted statuses require linked paper trades; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366
- promoted statuses require at least 30 IB Paper fills; package has 0.
- 271 event rows have blank anti-lookahead contract values.
- duplicate_group_id repeats exceed gate: 125/5619 rows (2.22%).
- 2995 experiment rows have nested_discovery_replay not implemented/passed.
- experiment rows report active blockers: EXP_PATTERN_000490_RR_1_5, EXP_PATTERN_000490_RR_2, EXP_PATTERN_000490_RR_2_5, EXP_PATTERN_000490_RR_3, EXP_PATTERN_000490_RR_4, EXP_PATTERN_000490_RR_5, EXP_PATTERN_000560_RR_1_5, EXP_PATTERN_000560_RR_2, EXP_PATTERN_000560_RR_2_5, EXP_PATTERN_000560_RR_3 (+182 more)

## Required next actions

- Keep all patterns in research/watchlist until paper trades are exported.
- Ingest IB Paper fills with commissions, spread and slippage before promotion.