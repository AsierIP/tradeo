# P0 Grid Sampling Precision Fix

## Scope

Implements the V1 Precision P0 fix for biased self-improvement grid sampling.
The previous mutation loop enumerated the cartesian grid lexicographically and
then truncated to `self_improvement_max_trials`, which could freeze early axes
at their first values when the budget was smaller than the full grid.

## External Report Sections Addressed

- V1 Precision P0: honest trial accounting and unbiased grid exploration.
- Section 5: ImprovementAgent anti-overfitting evidence must count and expose
  the actual search space explored.

## Files Changed

- `backend/tradeo/core/config.py`
- `backend/tradeo/services/self_improvement.py`
- `backend/tradeo/tests/test_self_improvement_grid_sampling.py`

## Behavior

- Adds deterministic stratified grid sampling with seed
  `self_improvement_sampling_seed`.
- Covers every axis value when the configured budget allows it.
- Samples without replacement and records `full_grid_size`, `sampled_count`,
  per-axis coverage and seed in the self-improvement report.
- Keeps existing PBO, plateau and nested outer-fold gates intact.

## Tests

- `backend/tradeo/tests/test_self_improvement_grid_sampling.py`

## Remaining Risks

- The sampler is discrete and deterministic. It does not make claims about
  global optimality; it only removes deterministic truncation bias and makes
  the explored subset auditable.
