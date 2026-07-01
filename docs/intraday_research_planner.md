# Intraday Research Planner

## Objective

The planner converts a completed intraday research wave into a compact next-step plan. It is read-only: it does not run research, relax gates, send orders, enable paper, or touch live trading.

It exists because broad waves over the clean `stock_only` universe have produced valid negative results. The next phase needs disciplined search-space rotation instead of repeating the same family.

## Inputs

The planner can use either a diagnostic JSON payload or explicit CLI summary flags. Important fields are selected count, readiness coverage, windows, clusters, accepted/rejected counts, persisted candidates, blockers, exact rejection reasons and near-miss candidate metrics.

## Decisions

The planner emits one of:

- `data_missing`: readiness is not good enough; warm cache before research.
- `expand_universe`: selected stock-only universe is still below the serious-search threshold.
- `candidate_for_confirmation`: a candidate deserves narrow confirmation, not paper.
- `change_search_space`: last wave was a valid negative result; rotate timeframe/window/exit family.
- `continue_matrix`: reserved for future matrix workflows.

## Safety rules

Every plan records that paper, live, order-code changes and gate relaxation are not allowed. It also requires rejected candidate persistence and exact-scope diagnostics.

## Current search philosophy

When costs dominate, the planner prioritizes higher timeframe and slower exits. When OOS, drawdown or robustness failures dominate, it proposes larger pattern windows and regime probes.

The first proposed families are usually:

- `1h_W50_cost_aware`, forward bars `2,4,6`.
- `30m_W100_slow_exit`, forward bars `8,13,21`.
- `30m_W100_standard_regime_probe`, forward bars `4,8,13`.

These are research experiments, not trading recommendations.

## CLI example

```bash
python3 /app/scripts/plan_intraday_research_next.py \
  --selected-count 117 \
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
