# Director Gate Result

- Created at: `2026-06-09T05:14:12+00:00`
- Package: `/home/vboxuser/tradeo/research/audit_bridge/requests/TRADEO-AUDIT-20260609-051406_daily_internal`
- Status: `blocked`

## Blockers

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
- independent_sample_count is not reconstructable from exported event rows for 500 patterns.
- market_regime is not persisted; cross-regime robustness cannot be audited.
- sector is not persisted; cross-sector concentration cannot be audited.
- no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.
- no train-only fit evidence fields found; cannot prove scaler/clustering/R:R selection avoided OOS contamination.
- 2985 experiment variants were exported without multiple-testing adjusted evidence.

## Summary

```json
{
  "patterns": 500,
  "events": 5856,
  "paper_trades": 0,
  "fills": 0,
  "experiments": 2985,
  "promoted_patterns": 3,
  "promoted_pattern_ids_preview": [
    "PATTERN_000282",
    "PATTERN_000364",
    "PATTERN_000366"
  ],
  "unknown_statuses": [],
  "duplicate_repeated_rows": 500,
  "duplicate_repeated_row_share": 0.085383,
  "non_independent_event_rows": 500,
  "pending_independence_rows": 500,
  "sample_count_mismatch_patterns": 500,
  "missing_oos_experiments": 2985,
  "missing_lookahead_columns": [
    "available_data_cutoff_ts",
    "decision_ts",
    "entry_eligible_ts",
    "label_generated_ts",
    "source_bar_hash",
    "split_id"
  ],
  "research_metric_column_offenders": 497,
  "train_only_evidence_missing": true,
  "director_gate": "blocked"
}
```
