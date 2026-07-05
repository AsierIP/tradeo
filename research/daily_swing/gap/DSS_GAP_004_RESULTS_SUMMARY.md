# DSS-GAP-004 Results Summary

Decision: DRY_RUN_METRICS_COMPLETE_NO_CANDIDATE_APPROVAL

Sanitized summary files:
- `research/daily_swing/gap/dss_gap_004_results_summary_by_family.csv`
- `research/daily_swing/gap/dss_gap_004_results_summary_by_policy.csv`
- `research/daily_swing/gap/dss_gap_004_results_summary_top_observations.csv`

Family summary:
- GAP_CONTINUATION_NEXT_DAY: 23 tests, 415178 events, 232279 OOS events, gross weighted expectancy 0.00004632.
- GAP_CONTINUATION_SAME_DAY: 23 tests, 415178 events, 232279 OOS events, gross weighted expectancy -0.00086251.
- GAP_REVERSAL_NEXT_DAY: 23 tests, 415178 events, 232279 OOS events, gross weighted expectancy -0.00004632.
- GAP_REVERSAL_SAME_DAY: 23 tests, 415178 events, 232279 OOS events, gross weighted expectancy 0.00086251.

Observations:
- The top net-x3 observation is GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL with OOS events 3495 and expectancy_net_x3 0.00132996.
- The four `DESIGN_VOLUME_T_MINUS_1` rows have zero events because previous-volume data is not present in GAP-002A; same-day `volume` was not used as a substitute.
- These are observations only. No threshold, family, policy, or candidate is selected.
- Baselines and placebos are present in the executed matrix and remain research-only controls.
- Same-day open slippage stress is included in the runtime per-test sensitivity field.

Conclusion:
- No paper-ready, shadow-ready, live-ready, or research-pass terminal claim is made.
