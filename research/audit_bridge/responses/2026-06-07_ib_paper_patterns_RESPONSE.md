# Director Audit Response: 2026-06-07_ib_paper_patterns

## Verdict

`NEEDS_PROCESS_IMPROVEMENT`

No pattern is approved for operation, extended paper trading, live trading, or automated execution from this package.

## Director score

`30 / 100`

| Area | Score | Reason |
|---|---:|---|
| Data integrity / reproducibility | 8 / 15 | Manifest, configs, hashes and references exist, but row-level lineage is incomplete and sample counts are not fully reconstructable from exported raw events. |
| Leakage & timestamp safety | 10 / 20 | No direct `uses_future_data=true` claim was found, but the package needs stricter timestamp cutoff fields and a raw event ledger. |
| Statistical robustness | 4 / 20 | Many patterns and RR variants were searched, but bootstrap, permutation, deflated Sharpe, adjusted p-values and outlier tests are missing. |
| OOS / walk-forward evidence | 0 / 15 | No usable OOS or walk-forward proof for approval. |
| Execution realism & costs | 0 / 15 | `paper_trades.csv` and `ib_fills.csv` have zero rows; spread, slippage and fills are unavailable. |
| Cross-ticker / cross-regime stability | 3 / 10 | Ticker counts exist, but market regime and sector are not persisted. |
| Economic plausibility | 5 / 5 | The cluster hypothesis is plausible enough for more research, not for promotion. |

## Confidence

`medium`

I reviewed the audit package, the exporter/validator logic, and PR #4 scope. I did not rerun the full lab from raw IBKR data, so the verdict is conservative.

## Executive summary

The Researcher produced a useful first audit package: 297 detected patterns, 3,685 exported representative events, and 1,737 RR experiment variants. However, it contains zero paper trades and zero IB fills. Therefore the reported profit factor, expectancy and drawdown values are research R-metrics, not realized or paper-execution PnL.

The main conclusion is not which pattern is best. The main conclusion is that the lab needs a stricter promotion gate. Pattern rankings based only on sample count or simulated R outcomes must stay in research until they survive a full event ledger export, explicit OOS/walk-forward validation, multiple-testing correction, and controlled paper execution with recorded fills/costs.

## Positive evidence

1. The package is traceable to a branch/commit and includes a manifest, configs, file hashes, code references and known limitations.
2. Failed/discarded variants are not hidden: the package exports 1,737 RR variants.
3. Most patterns are already marked `rejected`, which is directionally conservative.
4. The Researcher explicitly states that no pattern is approved because paper/live execution validation is unavailable.
5. The package separates catalog, events, per-pattern metrics, per-ticker metrics and per-period metrics.

## Negative evidence / risks

1. `paper_trades.csv` is empty.
2. `ib_fills.csv` is empty.
3. Bid, ask and spread are not persisted in the current event export.
4. Slippage is not observed yet.
5. Market regime and sector are not persisted, so cross-regime and cross-sector robustness cannot be audited.
6. The universe lacks delisted symbols, so survivorship bias remains open.
7. The export contains duplicated event groups and events whose independence is not fully resolved.
8. `sample_count` and `independent_sample_count` are not sufficiently separated from the exported row-level event ledger for approval purposes.
9. The PR description originally said documentation only, while the PR also changes backend IBKR/data-provider code and includes a large audit package.

## Blocking issues

- `BLOCK_EXECUTION_VALIDATION_MISSING`: zero paper trades and zero fills.
- `BLOCK_COST_MODEL_INCOMPLETE`: no realized spread, slippage, commissions or fill-quality data.
- `BLOCK_OOS_MISSING`: no usable OOS/walk-forward proof.
- `BLOCK_SAMPLE_LEDGER_INCOMPLETE`: exported events are representative rather than a complete immutable event ledger.
- `BLOCK_REGIME_AUDIT_MISSING`: regime and sector are not persisted.
- `BLOCK_MULTIPLE_TESTING`: 1,737 tested variants require adjusted statistical evidence before ranking.
- `BLOCK_PR_SCOPE_MISMATCH`: PR metadata must match actual code/data scope.

## Required next actions for Claw/Codex

1. Use `research/audit_bridge/director_gate.py` as the strict Director promotion gate.
2. Export the full immutable event ledger, not just representative examples.
3. Persist `available_data_cutoff_ts`, `decision_ts`, `entry_eligible_ts`, `label_generated_ts`, and raw bar/source hashes.
4. Recompute pattern status so any pattern with zero paper trades/fills cannot remain `paper_candidate`, `premium_candidate`, or any stronger status.
5. Add OOS/walk-forward, ticker holdout and period holdout outputs.
6. Add bootstrap, permutation test and multiple-testing adjustment fields.
7. Add regime/sector persistence and `metrics_by_regime.csv`.
8. Add paper trade/fill ingestion into future audit packages, including commission, spread, slippage and borrow assumptions for shorts.
9. Keep unauthenticated health endpoints free of balances and account identifiers.
10. Fix PR metadata/scope so the pull request body matches the actual changes.

## Process improvements ordered

- New strict mode: `python research/audit_bridge/director_gate.py <package>`.
- Any package may be schema-valid while still Director-gate-blocked.
- Promotion states are blocked until the package contains sufficient paper trades and fills.
- Research R-metrics must never be presented as net PnL.
- `sample_count` from upstream discovery must be distinct from `exported_event_count` and `independent_event_count_verified`.

## Promotion decision

`repeat_with_fixes`

The next package should not try to promote a pattern. It should prove that the research process can produce a complete, auditable ledger and then rerun the best few candidates through OOS/paper validation.

## Human notes

No live trading. No automated paper expansion. Keep this branch in review until the Director gate, security fix and audit-response files are merged or the PR is split into smaller scopes.
