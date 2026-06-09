# Director Gate Result

- Created at: `2026-06-09T15:03:25+00:00`
- Package: `/home/vboxuser/tradeo/research/audit_bridge/requests/TRADEO-AUDIT-20260609-1502_cron_lab_research`
- Status: `blocked`

## Blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- promoted statuses require linked paper trades; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366
- promoted statuses require at least 30 IB Paper fills; package has 2.
- research R metrics are populated in operational metric columns while trade_count is zero; offenders: PATTERN_000200, PATTERN_000466, PATTERN_000410, PATTERN_000617, PATTERN_000103, PATTERN_000349, PATTERN_000223, PATTERN_000258, PATTERN_000237, PATTERN_000490 (+110 more)
- duplicate_group_id repeats exceed gate: 189/1459 rows (12.95%).
- 190 event rows are not verified independent samples.
- 190 event rows have pending/unknown independence labels.
- independent_sample_count is not reconstructable from exported event rows for 120 patterns.
- no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.
- no train-only fit evidence fields found; cannot prove scaler/clustering/R:R selection avoided OOS contamination.
- 720 experiment variants were exported without multiple-testing adjusted evidence.

## Summary

```json
{
  "patterns": 120,
  "events": 1459,
  "paper_trades": 0,
  "fills": 2,
  "experiments": 720,
  "promoted_patterns": 3,
  "promoted_pattern_ids_preview": [
    "PATTERN_000282",
    "PATTERN_000364",
    "PATTERN_000366"
  ],
  "unknown_statuses": [],
  "duplicate_repeated_rows": 189,
  "duplicate_repeated_row_share": 0.129541,
  "non_independent_event_rows": 190,
  "pending_independence_rows": 190,
  "sample_count_mismatch_patterns": 120,
  "missing_oos_experiments": 720,
  "missing_lookahead_columns": [],
  "research_metric_column_offenders": 120,
  "train_only_evidence_missing": true,
  "director_gate": "blocked"
}
```
