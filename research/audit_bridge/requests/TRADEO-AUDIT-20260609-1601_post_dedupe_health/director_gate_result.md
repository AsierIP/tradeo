# Director Gate Result

- Created at: `2026-06-09T16:01:00+00:00`
- Package: `/home/vboxuser/tradeo/research/audit_bridge/requests/TRADEO-AUDIT-20260609-1601_post_dedupe_health`
- Status: `blocked`

## Blockers

- paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.
- ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.
- promoted statuses require linked paper trades; offenders: PATTERN_000282, PATTERN_000364, PATTERN_000366
- promoted statuses require at least 30 IB Paper fills; package has 0.
- duplicate_group_id repeats exceed gate: 92/1371 rows (6.71%).
- 102 event rows are not verified independent samples.
- 102 event rows have pending/unknown independence labels.
- independent_sample_count is not reconstructable from exported event rows for 120 patterns.
- no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.
- no train-only fit evidence fields found; cannot prove scaler/clustering/R:R selection avoided OOS contamination.
- 720 experiment variants were exported without multiple-testing adjusted evidence.

## Recommendations

- `P0` `keep_all_patterns_research_only`: paper_trades.csv has zero rows; no closed_lab_trades can confirm any pattern
- `P0` `ingest_ib_paper_fills`: fills, commissions, spread and slippage are unavailable
- `P0` `deduplicate_or_explain_events`: duplicate event rows can inflate sample counts and apparent edge
- `P0` `add_oos_and_train_only_evidence`: Director cannot separate discovery from validation without split evidence
- `P1` `prioritize_controlled_confirmation`: these patterns have samples/tickers but no paper confirmation

## Pattern Actions

- `PATTERN_000282` trades=0 remaining=30: freeze promoted status; needs 30 more linked paper trades before promotion evidence exists; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000364` trades=0 remaining=30: freeze promoted status; needs 30 more linked paper trades before promotion evidence exists; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000366` trades=0 remaining=30: freeze promoted status; needs 30 more linked paper trades before promotion evidence exists; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000047` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000284` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000413` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000128` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000453` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000059` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000262` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000316` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000016` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000332` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000433` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000177` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000183` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000492` trades=0 remaining=30: promising research candidate without confirmation; collect controlled paper trades before ranking by PnL; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000225` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000201` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000620` trades=0 remaining=30: promising research candidate without confirmation; collect controlled paper trades before ranking by PnL; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000583` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000494` trades=0 remaining=30: promising research candidate without confirmation; collect controlled paper trades before ranking by PnL; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000061` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000469` trades=0 remaining=30: promising research candidate without confirmation; collect controlled paper trades before ranking by PnL; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000205` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000060` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000175` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000490` trades=0 remaining=30: promising research candidate without confirmation; collect controlled paper trades before ranking by PnL; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000470` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000560` trades=0 remaining=30: promising research candidate without confirmation; collect controlled paper trades before ranking by PnL; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000068` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000081` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000349` trades=0 remaining=30: broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000258` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000388` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000260` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000058` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000320` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000070` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key
- `PATTERN_000046` trades=0 remaining=30: collect 30 more closed paper trades before Director review; entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id; regime performance unavailable; missing closed_lab_trades with regime_key

## Summary

```json
{
  "patterns": 120,
  "events": 1371,
  "paper_trades": 0,
  "fills": 0,
  "experiments": 720,
  "promoted_patterns": 3,
  "promoted_pattern_ids_preview": [
    "PATTERN_000282",
    "PATTERN_000364",
    "PATTERN_000366"
  ],
  "unknown_statuses": [],
  "duplicate_repeated_rows": 92,
  "duplicate_repeated_row_share": 0.067104,
  "non_independent_event_rows": 102,
  "pending_independence_rows": 102,
  "sample_count_mismatch_patterns": 120,
  "missing_oos_experiments": 720,
  "missing_lookahead_columns": [],
  "research_metric_column_offenders": 0,
  "train_only_evidence_missing": true,
  "by_regime": {
    "available": false,
    "buckets": [],
    "empty_reason": "no_closed_lab_trades: missing closed_lab_trades with signal.metadata_json.regime.regime_key; paper_trades.csv has no matching closed trades."
  },
  "by_entry_variant": {
    "available": false,
    "buckets": [],
    "empty_reason": "no_closed_lab_trades: missing closed_lab_trades with signal.metadata_json.entry_variant_id; paper_trades.csv has no matching closed trades."
  },
  "actionable_recommendations": [
    {
      "action": "keep_all_patterns_research_only",
      "priority": "P0",
      "reason": "paper_trades.csv has zero rows; no closed_lab_trades can confirm any pattern",
      "required_data": "at least 30 linked paper trades for any promoted pattern"
    },
    {
      "action": "ingest_ib_paper_fills",
      "priority": "P0",
      "reason": "fills, commissions, spread and slippage are unavailable",
      "required_data": "at least 30 anonymized IB Paper fills for promoted patterns"
    },
    {
      "action": "deduplicate_or_explain_events",
      "priority": "P0",
      "reason": "duplicate event rows can inflate sample counts and apparent edge"
    },
    {
      "action": "add_oos_and_train_only_evidence",
      "priority": "P0",
      "reason": "Director cannot separate discovery from validation without split evidence"
    },
    {
      "action": "prioritize_controlled_confirmation",
      "priority": "P1",
      "patterns": [
        "PATTERN_000492",
        "PATTERN_000620",
        "PATTERN_000494",
        "PATTERN_000469",
        "PATTERN_000490",
        "PATTERN_000560"
      ],
      "reason": "these patterns have samples/tickers but no paper confirmation"
    }
  ],
  "pattern_recommendation_count": 120,
  "pattern_recommendations": [
    {
      "pattern_id": "PATTERN_000282",
      "pattern_name": "DISCOVERED_LONG_W20_C05_43AA830F",
      "status": "paper_candidate",
      "independent_sample_count": 114,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "freeze promoted status; needs 30 more linked paper trades before promotion evidence exists",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000364",
      "pattern_name": "DISCOVERED_SHORT_W50_C05_BBCCAF14",
      "status": "paper_candidate",
      "independent_sample_count": 111,
      "ticker_count": 18,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "freeze promoted status; needs 30 more linked paper trades before promotion evidence exists",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000366",
      "pattern_name": "DISCOVERED_SHORT_W50_C06_D53F85BD",
      "status": "paper_candidate",
      "independent_sample_count": 106,
      "ticker_count": 19,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "freeze promoted status; needs 30 more linked paper trades before promotion evidence exists",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000047",
      "pattern_name": "DISCOVERED_LONG_W20_C01_AF0AFDF9",
      "status": "rejected",
      "independent_sample_count": 1060,
      "ticker_count": 24,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000284",
      "pattern_name": "DISCOVERED_LONG_W20_C03_BEBBB87A",
      "status": "rejected",
      "independent_sample_count": 644,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000413",
      "pattern_name": "DISCOVERED_LONG_W20_C03_27E7715B",
      "status": "rejected",
      "independent_sample_count": 438,
      "ticker_count": 13,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000128",
      "pattern_name": "DISCOVERED_LONG_W20_C08_2A34E2D6",
      "status": "rejected",
      "independent_sample_count": 212,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000453",
      "pattern_name": "DISCOVERED_LONG_W20_C02_A1FABD04",
      "status": "rejected",
      "independent_sample_count": 206,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000059",
      "pattern_name": "DISCOVERED_LONG_W20_C11_484F3A29",
      "status": "rejected",
      "independent_sample_count": 184,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000262",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_DA0B95F5",
      "status": "rejected",
      "independent_sample_count": 182,
      "ticker_count": 19,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000316",
      "pattern_name": "DISCOVERED_LONG_W20_C02_F2E76BEA",
      "status": "rejected",
      "independent_sample_count": 172,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000016",
      "pattern_name": "DISCOVERED_SHORT_W50_C06_6C7C8BB7",
      "status": "rejected",
      "independent_sample_count": 150,
      "ticker_count": 20,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000332",
      "pattern_name": "DISCOVERED_SHORT_W20_C05_2A303029",
      "status": "rejected",
      "independent_sample_count": 149,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000433",
      "pattern_name": "DISCOVERED_LONG_W20_C01_4A2C6E6F",
      "status": "rejected",
      "independent_sample_count": 144,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000177",
      "pattern_name": "DISCOVERED_SHORT_W20_C05_4A0EE5FC",
      "status": "rejected",
      "independent_sample_count": 129,
      "ticker_count": 2,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000183",
      "pattern_name": "DISCOVERED_SHORT_W50_C01_2F677116",
      "status": "rejected",
      "independent_sample_count": 125,
      "ticker_count": 9,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000492",
      "pattern_name": "DISCOVERED_SHORT_W50_C01_85A05D85",
      "status": "lab_candidate",
      "independent_sample_count": 124,
      "ticker_count": 14,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000225",
      "pattern_name": "DISCOVERED_LONG_W20_C04_04EF2C14",
      "status": "rejected",
      "independent_sample_count": 124,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000201",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_B1AF15AF",
      "status": "rejected",
      "independent_sample_count": 122,
      "ticker_count": 21,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000620",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_9BE87280",
      "status": "lab_candidate",
      "independent_sample_count": 121,
      "ticker_count": 21,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000583",
      "pattern_name": "DISCOVERED_SHORT_W50_C11_B3A70DDE",
      "status": "rejected",
      "independent_sample_count": 119,
      "ticker_count": 16,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000494",
      "pattern_name": "DISCOVERED_SHORT_W50_C10_58F162DA",
      "status": "lab_watchlist",
      "independent_sample_count": 117,
      "ticker_count": 20,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000061",
      "pattern_name": "DISCOVERED_LONG_W20_C02_897C0469",
      "status": "rejected",
      "independent_sample_count": 113,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000469",
      "pattern_name": "DISCOVERED_SHORT_W50_C05_B3502794",
      "status": "lab_watchlist",
      "independent_sample_count": 110,
      "ticker_count": 14,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000205",
      "pattern_name": "DISCOVERED_LONG_W20_C02_141038FE",
      "status": "rejected",
      "independent_sample_count": 108,
      "ticker_count": 14,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000060",
      "pattern_name": "DISCOVERED_LONG_W20_C04_A58C27FA",
      "status": "rejected",
      "independent_sample_count": 105,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000175",
      "pattern_name": "DISCOVERED_LONG_W20_C02_FEF1E222",
      "status": "rejected",
      "independent_sample_count": 105,
      "ticker_count": 2,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000490",
      "pattern_name": "DISCOVERED_SHORT_W50_C03_38E81507",
      "status": "lab_candidate",
      "independent_sample_count": 103,
      "ticker_count": 16,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000470",
      "pattern_name": "DISCOVERED_SHORT_W50_C06_7AE97930",
      "status": "rejected",
      "independent_sample_count": 102,
      "ticker_count": 15,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000560",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_18ED21F8",
      "status": "lab_candidate",
      "independent_sample_count": 101,
      "ticker_count": 17,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000068",
      "pattern_name": "DISCOVERED_LONG_W50_C01_4C05BFF3",
      "status": "rejected",
      "independent_sample_count": 101,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000081",
      "pattern_name": "DISCOVERED_LONG_W20_C00_4512D515",
      "status": "rejected",
      "independent_sample_count": 101,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000349",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_DB64E1F9",
      "status": "rejected",
      "independent_sample_count": 100,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000258",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_DB295C4E",
      "status": "rejected",
      "independent_sample_count": 99,
      "ticker_count": 20,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000388",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_CC1A6072",
      "status": "rejected",
      "independent_sample_count": 97,
      "ticker_count": 16,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000260",
      "pattern_name": "DISCOVERED_SHORT_W50_C06_C5C763DB",
      "status": "rejected",
      "independent_sample_count": 96,
      "ticker_count": 12,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000058",
      "pattern_name": "DISCOVERED_LONG_W20_C00_2123368A",
      "status": "rejected",
      "independent_sample_count": 94,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000320",
      "pattern_name": "DISCOVERED_LONG_W20_C03_A44DA73A",
      "status": "rejected",
      "independent_sample_count": 94,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000070",
      "pattern_name": "DISCOVERED_LONG_W20_C05_48C37C4A",
      "status": "rejected",
      "independent_sample_count": 93,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000046",
      "pattern_name": "DISCOVERED_SHORT_W20_C01_13BE9FFF",
      "status": "rejected",
      "independent_sample_count": 92,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000390",
      "pattern_name": "DISCOVERED_SHORT_W50_C03_20DF1FD0",
      "status": "rejected",
      "independent_sample_count": 91,
      "ticker_count": 18,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000516",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_2087414A",
      "status": "rejected",
      "independent_sample_count": 90,
      "ticker_count": 17,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000621",
      "pattern_name": "DISCOVERED_SHORT_W50_C03_BD6A8746",
      "status": "rejected",
      "independent_sample_count": 89,
      "ticker_count": 19,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000283",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_8F29F884",
      "status": "rejected",
      "independent_sample_count": 89,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000584",
      "pattern_name": "DISCOVERED_SHORT_W50_C06_0D7D93C3",
      "status": "rejected",
      "independent_sample_count": 88,
      "ticker_count": 16,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000285",
      "pattern_name": "DISCOVERED_LONG_W20_C11_5DD631BF",
      "status": "rejected",
      "independent_sample_count": 87,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000143",
      "pattern_name": "DISCOVERED_SHORT_W50_C09_E6436663",
      "status": "rejected",
      "independent_sample_count": 84,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000106",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_10656C72",
      "status": "rejected",
      "independent_sample_count": 82,
      "ticker_count": 12,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000617",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_989C652E",
      "status": "rejected",
      "independent_sample_count": 81,
      "ticker_count": 11,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000491",
      "pattern_name": "DISCOVERED_SHORT_W50_C11_201AE277",
      "status": "rejected",
      "independent_sample_count": 80,
      "ticker_count": 10,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000223",
      "pattern_name": "DISCOVERED_LONG_W20_C02_6708F3E9",
      "status": "rejected",
      "independent_sample_count": 80,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000080",
      "pattern_name": "DISCOVERED_LONG_W20_C01_FAF17EEC",
      "status": "rejected",
      "independent_sample_count": 80,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000518",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_41718DDD",
      "status": "rejected",
      "independent_sample_count": 79,
      "ticker_count": 10,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000319",
      "pattern_name": "DISCOVERED_LONG_W20_C01_62C81CD3",
      "status": "rejected",
      "independent_sample_count": 79,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000317",
      "pattern_name": "DISCOVERED_LONG_W20_C01_3DACCBDC",
      "status": "rejected",
      "independent_sample_count": 79,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000582",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_16CE35DA",
      "status": "rejected",
      "independent_sample_count": 78,
      "ticker_count": 17,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000538",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_134DBD4A",
      "status": "rejected",
      "independent_sample_count": 78,
      "ticker_count": 13,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000539",
      "pattern_name": "DISCOVERED_SHORT_W50_C07_49AA6FDA",
      "status": "rejected",
      "independent_sample_count": 78,
      "ticker_count": 10,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000298",
      "pattern_name": "DISCOVERED_SHORT_W50_C01_094783A3",
      "status": "rejected",
      "independent_sample_count": 76,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000562",
      "pattern_name": "DISCOVERED_SHORT_W50_C01_DA0F1419",
      "status": "rejected",
      "independent_sample_count": 75,
      "ticker_count": 14,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000350",
      "pattern_name": "DISCOVERED_SHORT_W20_C09_E7AD1A5A",
      "status": "rejected",
      "independent_sample_count": 75,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000014",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_DDA81ECF",
      "status": "rejected",
      "independent_sample_count": 73,
      "ticker_count": 15,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000203",
      "pattern_name": "DISCOVERED_SHORT_W50_C05_EB6227A7",
      "status": "rejected",
      "independent_sample_count": 72,
      "ticker_count": 13,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000331",
      "pattern_name": "DISCOVERED_SHORT_W20_C02_DB7CF226",
      "status": "rejected",
      "independent_sample_count": 69,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000107",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_5BED805B",
      "status": "rejected",
      "independent_sample_count": 68,
      "ticker_count": 9,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000410",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_CD3D1332",
      "status": "rejected",
      "independent_sample_count": 67,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000200",
      "pattern_name": "DISCOVERED_SHORT_W50_C10_4142FAF4",
      "status": "rejected",
      "independent_sample_count": 66,
      "ticker_count": 14,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000336",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_65D8E1D4",
      "status": "rejected",
      "independent_sample_count": 66,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000411",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_AF94189C",
      "status": "rejected",
      "independent_sample_count": 65,
      "ticker_count": 11,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000363",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_9A6C2079",
      "status": "rejected",
      "independent_sample_count": 64,
      "ticker_count": 7,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000105",
      "pattern_name": "DISCOVERED_SHORT_W50_C11_3DDBA7B3",
      "status": "rejected",
      "independent_sample_count": 63,
      "ticker_count": 15,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000239",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_D85C37A7",
      "status": "rejected",
      "independent_sample_count": 63,
      "ticker_count": 5,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000337",
      "pattern_name": "DISCOVERED_LONG_W20_C11_50CF6AD3",
      "status": "rejected",
      "independent_sample_count": 63,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000467",
      "pattern_name": "DISCOVERED_SHORT_W50_C10_2C28691B",
      "status": "rejected",
      "independent_sample_count": 61,
      "ticker_count": 11,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000618",
      "pattern_name": "DISCOVERED_SHORT_W50_C09_2A26CD6D",
      "status": "rejected",
      "independent_sample_count": 60,
      "ticker_count": 17,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000412",
      "pattern_name": "DISCOVERED_LONG_W50_C03_54AE94BD",
      "status": "rejected",
      "independent_sample_count": 60,
      "ticker_count": 9,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000104",
      "pattern_name": "DISCOVERED_SHORT_W50_C03_910C25FE",
      "status": "rejected",
      "independent_sample_count": 59,
      "ticker_count": 18,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000015",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_E0DAC825",
      "status": "rejected",
      "independent_sample_count": 59,
      "ticker_count": 9,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000259",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_8B47A583",
      "status": "rejected",
      "independent_sample_count": 58,
      "ticker_count": 9,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000082",
      "pattern_name": "DISCOVERED_LONG_W20_C05_5041888B",
      "status": "rejected",
      "independent_sample_count": 58,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000365",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_B25A79C7",
      "status": "rejected",
      "independent_sample_count": 57,
      "ticker_count": 14,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000286",
      "pattern_name": "DISCOVERED_SHORT_W50_C03_F9594C79",
      "status": "rejected",
      "independent_sample_count": 57,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000435",
      "pattern_name": "DISCOVERED_LONG_W20_C04_FA9C1C2E",
      "status": "rejected",
      "independent_sample_count": 57,
      "ticker_count": 2,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000447",
      "pattern_name": "DISCOVERED_LONG_W20_C00_13FD818C",
      "status": "rejected",
      "independent_sample_count": 57,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000299",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_CDDE5007",
      "status": "rejected",
      "independent_sample_count": 56,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000315",
      "pattern_name": "DISCOVERED_LONG_W20_C03_D3B42B39",
      "status": "rejected",
      "independent_sample_count": 56,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000204",
      "pattern_name": "DISCOVERED_SHORT_W50_C07_22087A4C",
      "status": "rejected",
      "independent_sample_count": 55,
      "ticker_count": 11,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000237",
      "pattern_name": "DISCOVERED_SHORT_W50_C06_3282E3E4",
      "status": "rejected",
      "independent_sample_count": 55,
      "ticker_count": 10,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000468",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_705CA552",
      "status": "rejected",
      "independent_sample_count": 54,
      "ticker_count": 13,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000017",
      "pattern_name": "DISCOVERED_SHORT_W50_C09_DF73462A",
      "status": "rejected",
      "independent_sample_count": 54,
      "ticker_count": 10,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000619",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_D1B0940D",
      "status": "rejected",
      "independent_sample_count": 53,
      "ticker_count": 11,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000127",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_C9B4835A",
      "status": "rejected",
      "independent_sample_count": 53,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000515",
      "pattern_name": "DISCOVERED_SHORT_W50_C07_20B54A1F",
      "status": "rejected",
      "independent_sample_count": 52,
      "ticker_count": 13,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000432",
      "pattern_name": "DISCOVERED_LONG_W20_C03_49116A34",
      "status": "rejected",
      "independent_sample_count": 52,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000071",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_720DF47C",
      "status": "rejected",
      "independent_sample_count": 52,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000182",
      "pattern_name": "DISCOVERED_LONG_W50_C06_BDC79400",
      "status": "rejected",
      "independent_sample_count": 51,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000517",
      "pattern_name": "DISCOVERED_LONG_W50_C11_18982D2D",
      "status": "rejected",
      "independent_sample_count": 49,
      "ticker_count": 16,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000013",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_F47180E1",
      "status": "rejected",
      "independent_sample_count": 49,
      "ticker_count": 7,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000238",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_58E580BC",
      "status": "rejected",
      "independent_sample_count": 48,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000224",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_41D516BE",
      "status": "rejected",
      "independent_sample_count": 48,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000202",
      "pattern_name": "DISCOVERED_SHORT_W50_C08_5A9FE370",
      "status": "rejected",
      "independent_sample_count": 47,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000129",
      "pattern_name": "DISCOVERED_SHORT_W50_C01_BF7BA9DD",
      "status": "rejected",
      "independent_sample_count": 45,
      "ticker_count": 2,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000537",
      "pattern_name": "DISCOVERED_SHORT_W50_C03_6F238DAA",
      "status": "rejected",
      "independent_sample_count": 43,
      "ticker_count": 10,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000493",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_7F45363A",
      "status": "rejected",
      "independent_sample_count": 41,
      "ticker_count": 9,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000261",
      "pattern_name": "DISCOVERED_SHORT_W50_C09_6412D8A7",
      "status": "rejected",
      "independent_sample_count": 41,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000466",
      "pattern_name": "DISCOVERED_SHORT_W50_C00_CE8AA7CF",
      "status": "rejected",
      "independent_sample_count": 41,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000144",
      "pattern_name": "DISCOVERED_LONG_W50_C01_8C9CBF25",
      "status": "rejected",
      "independent_sample_count": 41,
      "ticker_count": 3,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000387",
      "pattern_name": "DISCOVERED_SHORT_W50_C04_AE70270F",
      "status": "rejected",
      "independent_sample_count": 40,
      "ticker_count": 5,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000311",
      "pattern_name": "DISCOVERED_LONG_W20_C04_0A636D40",
      "status": "rejected",
      "independent_sample_count": 40,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000351",
      "pattern_name": "DISCOVERED_SHORT_W50_C01_98900E01",
      "status": "rejected",
      "independent_sample_count": 37,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000622",
      "pattern_name": "DISCOVERED_SHORT_W50_C10_1C444BC6",
      "status": "rejected",
      "independent_sample_count": 36,
      "ticker_count": 8,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000160",
      "pattern_name": "DISCOVERED_LONG_W20_C09_E469ED13",
      "status": "rejected",
      "independent_sample_count": 35,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000561",
      "pattern_name": "DISCOVERED_SHORT_W50_C10_33D735AC",
      "status": "rejected",
      "independent_sample_count": 34,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000069",
      "pattern_name": "DISCOVERED_LONG_W50_C00_DB2FF044",
      "status": "rejected",
      "independent_sample_count": 34,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000103",
      "pattern_name": "DISCOVERED_SHORT_W50_C10_CC719DB4",
      "status": "rejected",
      "independent_sample_count": 31,
      "ticker_count": 4,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000318",
      "pattern_name": "DISCOVERED_SHORT_W20_C00_DC0278A5",
      "status": "rejected",
      "independent_sample_count": 31,
      "ticker_count": 1,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000035",
      "pattern_name": "DISCOVERED_SHORT_W50_C05_09EBA0CA",
      "status": "rejected",
      "independent_sample_count": 30,
      "ticker_count": 13,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000389",
      "pattern_name": "DISCOVERED_LONG_W50_C09_D2C613A0",
      "status": "rejected",
      "independent_sample_count": 30,
      "ticker_count": 6,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000514",
      "pattern_name": "DISCOVERED_SHORT_W50_C02_425F8549",
      "status": "rejected",
      "independent_sample_count": 30,
      "ticker_count": 5,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    },
    {
      "pattern_id": "PATTERN_000176",
      "pattern_name": "DISCOVERED_LONG_W20_C09_58EDFF7A",
      "status": "rejected",
      "independent_sample_count": 30,
      "ticker_count": 2,
      "trade_count": 0,
      "trades_remaining_for_promotion": 30,
      "best_entry_variant": {},
      "worst_entry_variant": {},
      "best_regime": {},
      "worst_regime": {},
      "actions": [
        "collect 30 more closed paper trades before Director review",
        "entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id",
        "regime performance unavailable; missing closed_lab_trades with regime_key"
      ]
    }
  ],
  "director_gate": "blocked"
}
```
