# Internal Auditor Agent Review

- Audit ID: `TRADEO-AUDIT-20260609-051406_daily_internal`
- Status: `blocked`
- Priority: `P0`
- Promotion decision: `stay_in_research`

## Top blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.
- promoted statuses require linked paper trades; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366
- promoted statuses require at least 30 IB Paper fills; package has 0.
- research R metrics are populated in operational metric columns while trade_count is zero; offenders: PATTERN_000200, PATTERN_000466, PATTERN_000410, PATTERN_000103, PATTERN_000349, PATTERN_000223, PATTERN_000258, PATTERN_000237, PATTERN_000490, PATTERN_000104 (+487 more)
- event ledger lacks anti-lookahead cutoff columns: available_data_cutoff_ts, decision_ts, entry_eligible_ts, label_generated_ts, source_bar_hash, split_id
- same-bar close entry model lacks entry_eligible_ts proof; offenders: PATTERN_000200, PATTERN_000466, PATTERN_000410, PATTERN_000103, PATTERN_000349, PATTERN_000223, PATTERN_000258, PATTERN_000237, PATTERN_000490, PATTERN_000104 (+490 more)
- duplicate_group_id repeats exceed gate: 500/5856 rows (8.54%).
- 500 event rows are not verified independent samples.
- 500 event rows have pending/unknown independence labels.

## Required next actions

- Keep all patterns in research/watchlist until paper trades are exported.
- Ingest IB Paper fills with commissions, spread and slippage before promotion.
- Add explicit OOS/walk-forward boundaries and metrics.
- Persist market regime and sector, then regenerate metrics_by_regime.csv.