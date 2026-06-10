# Tradeo 12-Phase Compliance Matrix

Date: 2026-06-10

This matrix is intentionally compact. Each agent should append its own rows without removing other branches' work.

| Section | Area | Agent | Status | Evidence |
|---|---|---:|---|---|
| 3.5 | Canonical outcomes | C | Partial | `RewardRiskAnalyzer._simulate_sample_detail` and `Backtester._simulate_exit` delegate to `triple_barrier_outcome`; `WindowSampler` persists `forward_opens`. |
| 3.5 | Cost model | C | Partial | `tiered_round_trip_cost_r` added and used by backtester; Research continues to use existing execution cost metrics through canonical net R. |
| 3.6 | RR/N_trials accounting | C | Partial | Default RR grid reduced to `2.5,4.0`; existing `real_variant_count`/`multiple_testing_trials` counts configured RR levels. |
| 5 | ImprovementAgent anti-overfitting | C | Partial | Fixed trial budget, mandatory CSCV/PBO guard, PBO threshold, and plateau check added before lab candidate creation. |
| 6 | Backtester parity | C | Partial | Backtester exit path now uses canonical `triple_barrier_outcome` and shared tiered costs. |
| 8 | Config | C | Partial | `.env.example` and `Settings` expose RR and self-improvement guard defaults. |

## Agent C Test Evidence

- Full backend suite: 165 passed.
- Ruff: passed.

## Agent C Remaining Gaps

- True non-trade/skipped signal accounting should propagate beyond labels.
- ImprovementAgent is guarded but not yet a nested Optuna workflow.
- ShadowTracker canonical outcome parity remains for Agent D/future work.
