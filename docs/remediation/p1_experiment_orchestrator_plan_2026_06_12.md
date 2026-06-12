# P1 Experiment Orchestrator Plan

## Scope

Adds a deterministic planning/accounting layer for multi-module experiments.
It does not execute evaluators and cannot submit orders.

## External Report Sections Addressed

- §4.2: ExperimentOrchestrator for the full system.
- D-A2: self-improvement only mutated `cup_v0`; matcher, entry and
  meta-labeling spaces were outside the experiment accounting loop.

## Files Changed

- `backend/tradeo/services/experiment_orchestrator.py`
- `backend/tradeo/tests/test_experiment_orchestrator.py`

## Behavior

- Defines `ExperimentSpace` for module-specific parameter grids.
- Builds deterministic trial plans with the same unbiased `sample_grid`
  contract used by self-improvement.
- Each trial carries `trial_accounting` with budget, full grid size and
  `counts_toward_family_n_trials`.
- Default V1 Precision spaces cover:
  - `cup_detector`
  - `matcher`
  - `entry`
  - `meta_label`

## Tests

- Default spaces cover multiple modules.
- Plans are deterministic for a seed and change with a different seed.
- Trial accounting is present on every trial.
- Invalid experiment spaces fail fast.

## Remaining Risks

- Evaluators are named but not run here. Next step is wiring each evaluator
  behind its existing offline/paper-only gates and appending results to the
  global experiment ledger.
