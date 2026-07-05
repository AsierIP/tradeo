# DSS GAP-005 Family And Policy Forensics

Generated: 2026-07-05T15:50:58Z

This review compares families and policies without selecting a best threshold or approving any candidate.

## Family Summary

|family|rows|candidate_rows|avg_x2|avg_pf_x2|max_x2|max_x2_test_id|max_x2_baseline_group|max_control_x2|verdict|
|---|---|---|---|---|---|---|---|---|---|
|GAP_CONTINUATION_NEXT_DAY|23|7|-0.001670|0.804069|0.000400|GAP003_CONTINUATION-NEXT-DAY_ABS_3_0_BOTH_ALL|CANDIDATE_PRE_REGISTERED|-0.001923|mostly_rejected_or_weak|
|GAP_CONTINUATION_SAME_DAY|23|7|-0.003014|0.730109|0.000000|GAP003_CONTINUATION-SAME-DAY_DESIGN_VOLUME_T_MINUS_1|DESIGN_LOCKED_FILTER_OR_POLICY|-0.000877|mostly_rejected_or_weak|
|GAP_REVERSAL_NEXT_DAY|23|7|-0.002156|0.773212|0.000000|GAP003_REVERSAL-NEXT-DAY_DESIGN_VOLUME_T_MINUS_1|DESIGN_LOCKED_FILTER_OR_POLICY|-0.001372|mostly_rejected_or_weak|
|GAP_REVERSAL_SAME_DAY|23|7|-0.000812|0.876422|0.002330|GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL|CANDIDATE_PRE_REGISTERED|-0.000877|contains_promising_observation|

## Policy Summary

|policy|rows|avg_x2|avg_pf_x2|max_x2|max_x2_test_id|verdict|
|---|---|---|---|---|---|---|
|ALL_EVENTS_RESEARCH_ONLY|84|-0.001905|0.792708|0.002330|GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL|research_only_unconstrained_has_only_promising_rows|
|MAX_2_NEW_TRADES_PER_DAY|4|-0.002000|0.824828|-0.001512|GAP003_REVERSAL-NEXT-DAY_ABS_1_0_MAX2|operability_sensitivity_negative_or_not_supportive|
|ONE_ACTIVE_PER_SYMBOL|4|-0.002000|0.835222|-0.000877|GAP003_REVERSAL-SAME-DAY_DESIGN_ONE_ACTIVE|operability_sensitivity_negative_or_not_supportive|

## Readout

- Same-day reversal contains the only rows that satisfy the minimum forensic filters, but PF remains in the 1.1-1.2 warning band.
- Continuation same-day, continuation next-day, and reversal next-day are mostly weak or negative after x2/x3 costs.
- Portfolio policy sensitivity rows do not support immediate operability; this remains research-only.
- No row is promoted to candidate, paper_candidate, shadow_candidate, or live_candidate.
