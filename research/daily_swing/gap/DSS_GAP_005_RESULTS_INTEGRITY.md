# DSS GAP-005 Results Integrity

Generated: 2026-07-05T15:50:58Z

Decision: RESULTS_INTEGRITY_PASS

## Checks

- Expected matrix test_ids: 92
- Executed result rows: 92
- Missing test_ids: 0
- Extra test_ids: 0
- Duplicate test_ids: 0
- Missing critical metric rows: 0
- Safety flag issues: 0
- Runtime result files present: True

## Counts

Baseline groups: {'CANDIDATE_PRE_REGISTERED': 28, 'DELAYED_ENTRY': 4, 'DESIGN_LOCKED_FILTER_OR_POLICY': 28, 'DIRECTION_SENSITIVITY': 8, 'EARNINGS_SENSITIVITY': 4, 'MATCHED_NON_GAP': 4, 'PORTFOLIO_POLICY_SENSITIVITY': 4, 'RANDOM_MATCHED': 4, 'SIGN_INVERTED_GAP': 4, 'THRESHOLD_PERTURBATION': 4}

Families: {'GAP_CONTINUATION_NEXT_DAY': 23, 'GAP_CONTINUATION_SAME_DAY': 23, 'GAP_REVERSAL_NEXT_DAY': 23, 'GAP_REVERSAL_SAME_DAY': 23}

Policies: {'ALL_EVENTS_RESEARCH_ONLY': 84, 'MAX_2_NEW_TRADES_PER_DAY': 4, 'ONE_ACTIVE_PER_SYMBOL': 4}

## Integrity Notes

GAP-004 results are usable for forensic review. Runtime artifacts remain local inputs and are not intended for versioning; the final security scan must confirm they are not tracked.
