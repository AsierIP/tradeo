# DSS-004C-A Final Report

Generated: 2026-07-04

## Executive Summary

DSS-004C-A is complete cache-only. DSS-BO-001 remains economically strong in OOS, and the shifted placebos are positive but below the base. However, matched baselines do not confirm that the full breakout-after-contraction specification has independent edge: CONTRACTION_ONLY beats the frozen base in OOS expectancy and PF, and BREAKOUT_ONLY is close to the base.

Final decision: DSS_BO_001_BASELINE_EXPLAINED_FAIL.

No DSS-005, no paper preview, no signals, and no orders.

## Inputs

- Worktree: /home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001
- Branch: feature/daily-swing-paper-probe-001
- Cache: artifacts/runtime/daily_swing/daily_ohlcv
- Universe: artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv
- Operational symbols: 50
- Benchmarks: SPY/QQQ only for regime
- Range: 2023-07-05 to 2026-07-02
- OOS start: 2025-01-01
- last_valid_bar_date: 2026-07-02

## Placebo OOS Audit

Partial decision: PLACEBO_TIMING_WINDOW_WARNING.

Base OOS expectancy net x2 is 1.8694% with PF 1.5363. Placebos +1/+2/+3/+5/+10 are all positive, but none matches or beats the base. This suggests a timing window remains possible, not a tight one-day trigger.

## Matched Baseline Audit

Partial decision: BASELINE_FAIL.

CONTRACTION_ONLY produces OOS expectancy net x2 2.7408% and PF 1.9379, above the frozen DSS-BO-001 base. BREAKOUT_ONLY produces 1.8215% and PF 1.5129, close to the base. The edge is not proven specific to the combined breakout-after-contraction rule.

## Guard Result

Guard decision: PASS.

The audit excludes SPY/QQQ from trades, rejects the fake 2026-07-03 bar, uses last_valid_bar_date 2026-07-02, keeps signal at t and entry at t+1, and remains cache-only.

## Decision

DSS_BO_001_BASELINE_EXPLAINED_FAIL.

DSS-BO-001 should not move to DSS-005 paper preview from this evidence. The recommended next step is Director review before further DSS-BO-001 work. If research continues, it should explicitly test whether a contraction-only or simpler momentum/regime baseline is the actual candidate, without tuning OOS or creating operational previews.

## Artifacts

- research/daily_swing/DSS_004C_A_PLACEBO_OOS.md
- research/daily_swing/DSS_004C_A_MATCHED_BASELINES.md
- research/daily_swing/DSS_004C_A_GUARDS.md
- artifacts/runtime/daily_swing/dss_004c_a_placebo_oos.csv
- artifacts/runtime/daily_swing/dss_004c_a_placebo_oos_summary.json
- artifacts/runtime/daily_swing/dss_004c_a_matched_baselines.csv
- artifacts/runtime/daily_swing/dss_004c_a_matched_baselines_summary.json
- artifacts/runtime/daily_swing/dss_004c_a_guards_summary.json
- artifacts/runtime/daily_swing/dss_004c_a_decision.json
