# Director Audit Run

- Audit ID: `TRADEO-AUDIT-20260609-1601_post_dedupe_health`
- Cadence: `manual`
- Created at: `2026-06-09T16:01:01+00:00`
- Package: `research/audit_bridge/requests/TRADEO-AUDIT-20260609-1601_post_dedupe_health`
- Director gate status: `blocked`

## Commands

| name | exit_code |
|---|---:|
| export | 0 |
| director_gate | 0 |
| validate | 0 |

## Agent review

```json
{
  "audit_id": "TRADEO-AUDIT-20260609-1601_post_dedupe_health",
  "cadence": "manual",
  "agent": "tradeo-internal-daily-auditor",
  "model_profile": "gpt-5.5-xhigh-specified-in-skill; deterministic fallback used by runner",
  "status": "blocked",
  "priority": "P0",
  "failed_commands": [],
  "blocker_count": 11,
  "top_blockers": [
    "paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.",
    "ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.",
    "promoted statuses require linked paper trades; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366",
    "promoted statuses require at least 30 IB Paper fills; package has 0.",
    "duplicate_group_id repeats exceed gate: 92/1371 rows (6.71%).",
    "102 event rows are not verified independent samples.",
    "102 event rows have pending/unknown independence labels.",
    "independent_sample_count is not reconstructable from exported event rows for 120 patterns.",
    "no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.",
    "no train-only fit evidence fields found; cannot prove scaler/clustering/R:R selection avoided OOS contamination."
  ],
  "director_handoff": "ChatGPT Director must review weekly packs or any P0 blocker before promotion.",
  "promotion_decision": "stay_in_research",
  "required_next_actions": [
    "Keep all patterns in research/watchlist until paper trades are exported.",
    "Ingest IB Paper fills with commissions, spread and slippage before promotion.",
    "Add explicit OOS/walk-forward boundaries and metrics."
  ]
}
```
