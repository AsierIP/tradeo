# Task: 2026-06-07_ib_paper_patterns_director_gate_and_research_fixes

## From

ChatGPT Director

## To

Claw/Codex Researcher

## Related audit

`2026-06-07_ib_paper_patterns`

## Priority

`P0`

## Goal

Improve the Tradeo research audit process so detected patterns cannot be promoted from discovery metrics alone.

## Context

The current package exports 297 patterns, 3,685 representative events and 1,737 RR variants, but zero paper trades and zero IB fills. The Director verdict is `NEEDS_PROCESS_IMPROVEMENT`; no pattern is approved. The next work must improve the process before trying to select winners.

## Required inputs

- `research/audit_bridge/director_gate.py`
- `research/audit_bridge/validate_audit_package.py`
- `research/audit_bridge/export_audit_package.py`
- `research/audit_bridge/requests/2026-06-07_ib_paper_patterns/`
- Research DB models/endpoints that produce discovered patterns, examples, matches, runs, paper trades and fills
- IBKR paper execution logs/fills if available

## Actions

1. Run:
   ```bash
   python research/audit_bridge/director_gate.py research/audit_bridge/requests/2026-06-07_ib_paper_patterns
   ```
   Treat a Director-gate failure as expected for the current package.
2. Update the exporter so `sample_count`, `exported_event_count`, and `verified_independent_sample_count` are separate and auditable.
3. Export a full immutable event ledger rather than representative examples only. Include source row IDs, window hashes, raw data hashes, `available_data_cutoff_ts`, `decision_ts`, `entry_eligible_ts`, and `label_generated_ts`.
4. Block or demote statuses such as `paper_candidate`, `premium_candidate`, `paper_limited_candidate`, `paper_extended_candidate`, `approved`, or stronger whenever paper trades/fills are missing or below threshold.
5. Add OOS/walk-forward boundaries and outputs. Include ticker holdout and period holdout.
6. Add bootstrap, permutation test, and multiple-testing correction outputs. Preserve the total number of variants tested.
7. Persist market regime and sector, then add `metrics_by_regime.csv`.
8. Add paper trade/fill ingestion to future packages, including commission, spread, slippage, borrow costs for shorts, order type, fill time, and realized vs expected entry/exit.
9. Keep live trading disabled and do not modify production execution gates.
10. Keep PR metadata/scope aligned with actual code and data changes.

## Expected outputs

- Updated exporter and/or validators.
- A rerun audit package, or a follow-up package, with explicit Director gate result.
- A report explaining which checks are still blocked and why.
- Tests or fixture package proving the Director gate blocks zero-trade promotion.

## Acceptance criteria

- Base package validation can pass while Director promotion eligibility can fail with a distinct message/exit code.
- Current package is blocked by Director gate because it has zero paper trades/fills and missing OOS/regime evidence.
- No pattern with zero paper trades/fills appears as `paper_candidate`, `premium_candidate`, `approved`, or stronger in future packages.
- For every promoted pattern, sample counts can be reconstructed from exported events or are explicitly separated as upstream counts with hashes.
- Future ranking uses net-cost evidence, OOS evidence, adjusted multiple-testing evidence, and concentration checks.

## Constraints

- No live trading.
- No direct push to `main`.
- No secrets or account IDs in exported audit artifacts.
- Do not delete historical audit packages.
- Do not report gross or research R-metrics as net realized PnL.

## Response format

At completion, respond with:

- Estado: OK / BLOCKED / NEEDS_HUMAN
- Rama:
- Commits:
- Ficheros modificados:
- Validaciones ejecutadas:
- Resultados:
- Riesgos:
- Siguiente paso recomendado:
