# Intraday Research Planner

## Objective

The planner converts a completed intraday research wave into a compact next-step plan. It is read-only: it does not run research, relax gates, send orders, enable paper, or touch live trading.

It exists because broad waves over the clean `stock_only` universe have produced valid negative results. The next phase needs disciplined search-space rotation instead of repeating the same family.

## Inputs

The planner can use either a diagnostic JSON payload or explicit CLI summary
flags. Important fields are selected count, readiness coverage, windows,
clusters, accepted/rejected counts, persisted candidates, blockers, exact
rejection reasons and near-miss candidate metrics.

Selected count is resolved with fail-closed provenance. Priority:

1. `--selected-count`
2. `--universe-metadata`
3. `--universe-file`
4. `diagnostic_json.selected_count`
5. `diagnostic_json.scope.selected_count`
6. `0` only when no source is available

The output records:

- `selected_count_diagnostic_value`
- `selected_count_effective`
- `selected_count_source`
- `recommended_limit`
- `limit_source`

Do not run readiness or waves without explicit `--limit <selected_count_effective>`.

## Exact Wave Execution Contract

Before a terminal wave can be authorized, `scripts/run_intraday_research_wave.py`
must prove that `--execute` would run the exact same configuration that passed
readiness. CLI arguments are copied into the settings environment before
`get_settings()` and before the worker is called:

- `--universe-file`
- `--product-policy`
- `--period`
- `--timeframes`
- `--limit`
- `--window-sizes`
- `--forward-bars`
- `--max-total-windows`
- `--max-windows-per-symbol`

The wave manifest and CLI summary include `execution_spec`,
`readiness_spec_hash`, `execution_spec_hash` and `specs_match`. If `--execute`
is active and the hashes differ, the runner blocks with
`decision=blocked_spec_mismatch` and does not call the worker. Dry runs also
emit the execution contract so Director can audit the next authorized wave
without executing it.

## Decisions

The planner emits one of:

- `data_missing`: readiness is not good enough; warm cache before research.
- `expand_universe`: selected stock-only universe is still below the serious-search threshold.
- `candidate_for_confirmation`: a candidate deserves narrow confirmation, not paper.
- `change_search_space`: last wave was a valid negative result; rotate timeframe/window/exit family.
- `continue_matrix`: reserved for future matrix workflows.

## Safety rules

Every plan records that paper, live, order-code changes and gate relaxation are not allowed. It also requires rejected candidate persistence and exact-scope diagnostics.

## Prohibited Repeats

Diagnostics can include `prohibited_repeats`, for example:

- `30m W20 4,8,13`
- `30m W50 4,8,13`
- `30m W50 8,13,21`
- `1h W20 2,4,6`
- `1h W50 2,4,6`

The planner compares proposed wave signatures by timeframe, window size and
forward bars. Matching waves are removed from `allowed_waves` and emitted in
`blocked_waves` with `reason=prohibited_repeat`. Director-visible wave
recommendations must come from `allowed_waves`, never from blocked repeats.

## Current search philosophy

When costs dominate, the planner prioritizes higher timeframe and slower exits. When OOS, drawdown or robustness failures dominate, it proposes larger pattern windows and regime probes.

The first proposed families are usually:

- `30m_W100_slow_exit`, forward bars `8,13,21`.
- `30m_W100_standard_regime_probe`, forward bars `4,8,13`.
- `1h_W50_cost_aware`, forward bars `2,4,6`, only when it is not prohibited.

These are research experiments, not trading recommendations.

## CLI example

```bash
python3 /app/scripts/plan_intraday_research_next.py \
  --diagnostic-json artifacts/runtime/research_forensics/_forensics.json \
  --universe-metadata artifacts/runtime/universe_intraday_stock_only_v3.metadata.json \
  --universe-file artifacts/runtime/universe_intraday_stock_only_v3.csv \
  --windows 85436 \
  --clusters 48 \
  --accepted 0 \
  --rejected 48 \
  --persisted-candidates 48 \
  --blocker cost_stress_failed=94 \
  --blocker oos_expectancy_not_positive=86 \
  --blocker fdr_failed=88 \
  --json-out artifacts/runtime/research_plans/next_plan.json \
  --md-out artifacts/runtime/research_plans/next_plan.md
```

## Daily loop

1. Run one cache-ready wave.
2. Diagnose it by wave manifest or run IDs.
3. Feed the diagnostic summary to the planner.
4. Execute only the next approved family.
5. Never promote to paper from this planner alone.
