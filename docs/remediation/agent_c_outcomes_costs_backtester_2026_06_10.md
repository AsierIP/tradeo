# Agent C - Outcomes, Costs, Backtester, ImprovementAgent

Date: 2026-06-10
Branch: `agent-c-outcomes-costs-backtester`
Base: `origin/main` at `9cc7ccb`

## Scope

Implemented Agent C fallback remediation for outcomes, cost modeling, backtester parity, RR trial accounting defaults, and ImprovementAgent anti-overfitting guards.

No live trading was enabled. The change stays in Research/Lab/backtest code paths.

## External Report Sections Addressed

- 3.5 Outcomes: Research RR simulation now delegates to canonical `triple_barrier_outcome`, including next-open entry, pessimistic both-touch handling, gap skip policy, time exits, MFE/MAE, and net R costs.
- 3.6 Validation/RR accounting: RR defaults reduced to the two a priori levels `2.5,4.0`; existing `real_variant_count`/`multiple_testing_trials` now counts the smaller grid by default.
- 5 ImprovementAgent: lab mutation cycles now record fixed trial budgets, block acceptance without CSCV/PBO evidence, require `PBO < 0.10`, and require a local parameter plateau check.
- 6 Backtester: simulated exits now reuse `triple_barrier_outcome` and the shared tiered round-trip cost model instead of a separate optimistic high/low loop.
- 8 Config: `.env.example` and `Settings` now expose Agent C defaults for RR levels and self-improvement anti-overfit thresholds.

## Files Changed

- `.env.example`
- `backend/tradeo/core/config.py`
- `backend/tradeo/research/quant_validation.py`
- `backend/tradeo/research/reward_risk_analyzer.py`
- `backend/tradeo/research/types.py`
- `backend/tradeo/research/window_sampler.py`
- `backend/tradeo/services/backtester.py`
- `backend/tradeo/services/self_improvement.py`
- `backend/tradeo/tests/test_agent_c_remediation.py`
- `backend/tradeo/tests/test_reward_risk_analyzer.py`
- `docs/remediation/agent_c_outcomes_costs_backtester_2026_06_10.md`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`

## Tests Run

From `backend/` in a local `.venv`:

- `.venv/bin/pytest -q tradeo/tests/test_quant_validation.py tradeo/tests/test_reward_risk_analyzer.py tradeo/tests/test_agent_c_remediation.py`
  - 36 passed
- `.venv/bin/pytest -q tradeo/tests/test_pattern_discovery_lab.py tradeo/tests/test_quant_validation_integration.py tradeo/tests/test_autonomous_research_director.py`
  - 30 passed
- `.venv/bin/ruff check .`
  - passed
- `.venv/bin/pytest -q`
  - 165 passed, 1 warning from `eventkit` Python 3.14 deprecation

## Remaining Risks / Known Non-Compliance

- `RewardRiskAnalyzer` still represents skipped entry gaps as `0.0R` for compatibility with existing aggregate arrays. The label now records `skipped`, but future work should propagate true non-trade counts through every metric.
- Research uses the canonical outcome through RR simulation, but `WindowSampler` still precomputes legacy descriptive outcome fields for compatibility.
- ImprovementAgent now blocks without PBO/plateau evidence, but it is still a grid search, not full Optuna nested optimization.
- PBO is computed from monthly realized backtest R buckets. A richer outer-fold/nested report should be added when the ImprovementAgent gets a full optimizer.
- ShadowTracker parity is not in this scope; this branch only covers Research RR simulation and the backtester.

## Merge Notes

- This branch adds `ForwardOutcome.forward_opens` with a default empty list, so existing serialized objects remain compatible.
- `TRADEO_DISCOVERY_RR_LEVELS` default changes from six levels to `2.5,4.0`. If another branch assumes six levels, keep their explicit env override or reconcile docs.
- `SelfImprovementEngine` may accept fewer or zero lab candidates because PBO/plateau evidence is now mandatory. This is intentional anti-overfitting behavior.
