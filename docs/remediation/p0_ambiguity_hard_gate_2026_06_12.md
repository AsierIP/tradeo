# P0 Ambiguity Hard Gate

## Scope

Implements the V1 Precision matcher requirement that ambiguous matches have
"teeth": if two patterns are nearly tied on the same symbol/timeframe/window,
the matcher must demand stronger entry evidence or abstain.

## External Report Sections Addressed

- §3.1.4: Ambiguity with teeth.
- §1.2 D-L3: ambiguity was measured but not applied.

## Files Changed

- `backend/tradeo/core/config.py`
- `backend/tradeo/research/novel_pattern_matcher.py`
- `backend/tradeo/tests/test_pattern_entry_scanner.py`

## Behavior

- Adds `discovery_match_ambiguity_hard_gate_enabled` (default `true`).
- Adds configurable `discovery_match_ambiguity_ratio_threshold` and
  `discovery_match_ambiguity_entry_score_margin`.
- Ambiguous matches now require `entry_score >= entry_min_score + margin`.
  Otherwise they are abstained before signal candidates are emitted.
- Match results expose `ambiguity_gate_blocked` and per-match
  `ambiguity_gate` diagnostics.

## Tests

- `test_laboratory_matcher_records_feature_parity_and_ambiguity_ratio`
- `test_laboratory_matcher_hard_blocks_ambiguous_weak_entry`

## Remaining Risks

- This does not yet implement calibrated meta-label probabilities. When that
  exists, ambiguous matches should require `p_meta >= p_star + margin` as the
  report recommends.
