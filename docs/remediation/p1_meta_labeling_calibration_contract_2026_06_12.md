# P1 Meta-Labeling Calibration Contract

## Scope

Adds the audit-facing contract for meta-labeling probabilities before any model
is allowed to influence Lab/Fox entry decisions. This is intentionally not wired
to live execution.

## External Report Sections Addressed

- §2.4: Meta-labeling with calibrated probability.
- §3.2: Lab entry gate should eventually use calibrated `p_meta`.
- Anti-leakage requirement: features must be available at signal time.

## Files Changed

- `backend/tradeo/research/meta_labeling.py`
- `backend/tradeo/tests/test_meta_labeling.py`

## Behavior

- Computes Brier score, Expected Calibration Error, base win rate,
  precision/top-decile win rate, top-decile uplift, breakeven probability from
  RR and cost in R, and selected expectancy at breakeven.
- Fails closed on insufficient samples, non-binary labels, invalid
  probabilities or invalid sample weights.
- Adds `feature_leakage_guard` to compare stored decision-time features against
  features recomputed from a truncated signal-time dataframe.

## Tests

- Calibrated/selective synthetic probabilities pass.
- Flat model without uplift fails.
- Invalid/underpowered inputs block.
- Weighted ECE bins are deterministic.
- Feature leakage guard catches future-feature drift.

## Remaining Risks

- No predictor is trained yet. The next step is generating out-of-sample
  probabilities with purged/embargoed folds and wiring only passing reports
  into Lab as shadow diagnostics before any entry gate uses them.
