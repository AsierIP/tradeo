# Tradeo Research Process Improvements

## 2026-06-07 — Director audit gate and promotion hygiene

Status: `ordered`
Related audit: `2026-06-07_ib_paper_patterns`
Priority: `P0`

### Required improvements

1. Separate package schema validity from Director promotion eligibility.
2. Add a strict Director gate to block promotion without sufficient paper trades/fills.
3. Separate upstream `sample_count` from exported event count and verified independent sample count.
4. Export full event ledgers, not only representative examples.
5. Persist timestamp cutoff fields that prove no lookahead: `available_data_cutoff_ts`, `decision_ts`, `entry_eligible_ts`, `label_generated_ts`.
6. Add OOS/walk-forward, ticker holdout and period holdout outputs.
7. Add bootstrap, permutation and multiple-testing adjusted evidence.
8. Persist sector/regime and add regime metrics.
9. Add paper trade/fill cost realism: commission, spread, slippage, borrow, order type and fill quality.
10. Keep PR descriptions aligned with actual code and data changes.

### Non-negotiable rule

A pattern can be interesting for research with zero trades, but it cannot be approved, extended, or treated as operationally validated without paper trade and fill evidence.
