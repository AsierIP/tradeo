# P1 Conformal Match Threshold

## Scope

Adds a split-conformal threshold contract for matcher similarity and teaches the
matcher to honor a Research-persisted conformal threshold when present.

## External Report Sections Addressed

- §3.1.3: conformal threshold with finite-sample recall guarantee.
- §3.1.5: FPR at a selected threshold on negative banks.

## Files Changed

- `backend/tradeo/research/conformal_matching.py`
- `backend/tradeo/research/novel_pattern_matcher.py`
- `backend/tradeo/tests/test_conformal_matching.py`
- `backend/tradeo/tests/test_pattern_entry_scanner.py`

## Behavior

- `split_conformal_similarity_threshold()` computes a conservative threshold
  from calibration-set member similarities.
- `false_positive_rate_at_threshold()` evaluates negative-bank FPR at that
  threshold.
- `NovelPatternMatcher._effective_threshold()` now uses the strictest of:
  global floor, legacy `match_tau_similarity`, and
  `match_conformal_similarity_threshold`.
- No behavior changes for patterns without persisted conformal threshold.

## Tests

- Conformal threshold recall contract.
- Invalid/underpowered calibration inputs block.
- Negative-bank FPR at threshold.
- Matcher prefers conformal threshold over legacy tau when present.

## Remaining Risks

- Research still needs to persist calibration similarities and
  `match_conformal_similarity_threshold` during discovery. Until then, matcher
  behavior falls back to the existing per-pattern tau.
