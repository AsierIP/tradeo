# DSS-004H Terminal Candidate Matrix

Generated: 2026-07-04

Decision scope: close the current Daily Swing research line. This matrix is a terminal inventory, not a new search, signal preview, paper preview, or operational recommendation.

## Summary

| Candidate | Pattern | Universe | Policy | OOS trades | OOS symbols | OOS x2 expectancy | OOS PF x2 | Cost x3 expectancy | Top3 concentration | Bias / placebo / baseline | FDR / WRC / SPA | Final decision | Class |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| DSS-PB-001 | Pullback in uptrend long | 50 operational stocks + SPY/QQQ benchmarks | next open, 5-session time stop | 557 | 50 | -0.0573% | 0.9831 | 0.2522% | 39.06% | OOS negative after x2 costs; cost robustness insufficient | Not advanced to statistical family | DSS_PB_001_RESEARCH_FAIL | REJECTED_SPEC |
| DSS-BO-001 | Volatility contraction breakout long | 50 operational stocks + SPY/QQQ benchmarks | next open, 10-session time stop | 226 | 49 | 1.8694% | 1.5363 | 1.2829% | 30.73%; 33.90% in C-A | Placebos positive but lower; CONTRACTION_ONLY baseline dominates at 2.7408% / PF 1.9379 | Baseline fail blocks promotion | DSS_BO_001_BASELINE_EXPLAINED_FAIL | BASELINE_EXPLAINED_FAIL |
| DSS-CO-001 | Contraction in uptrend long | research-150 + SPY/QQQ benchmarks | ONE_ACTIVE_PER_SYMBOL primary; MAX2 comparison weaker | 1311 primary / 576 MAX2 | 147 primary / 116 MAX2 | 0.9723% primary / 0.4572% MAX2 | 1.3524 primary / 1.1930 MAX2 | 0.5051% primary / 0.1914% MAX2 | 14.44% primary / 19.45% MAX2 | Bias fail; timing/effective-sample warning; effect is research-interesting but not paper-grade | No final FDR/WRC/SPA pass; carried into CW design only | DSS_CO_001_RESEARCH_WARNING_RESEARCH150 / DSS_004F_CANONICAL_EFFECTIVE_SAMPLE_WARNING | TIMING_WINDOW_WARNING |
| DSS-CW-001 | Contraction window long | research-150 + SPY/QQQ benchmarks | MAX_2_NEW_EPISODES_PER_DAY | 529 | 137 | 0.8739% | 1.3802 | 0.5898% | 17.64% | Placebos +1 and +2 dominate base; base rank 3 | FDR_PLACEBO_DOMINANCE_FAIL; WRC_SPA_PLACEBO_BEST_FAIL; TIMING_PLACEBO_DOMINANCE_FAIL | DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC | FAIL_TIMING_NOT_SPECIFIC |

## Candidate Notes

### DSS-PB-001

Pullback in Uptrend Long failed as a research candidate. The OOS x2 net expectancy is negative (-0.0573%) with PF 0.9831, despite a positive all-sample cost x3 figure. This is not a paper, shadow, or signal candidate.

### DSS-BO-001

Volatility Contraction Breakout Long looked strong on headline OOS metrics, but DSS-004C-A rejected it because the simpler CONTRACTION_ONLY matched baseline outperformed the base strategy. The candidate is therefore explained by a simpler contraction/regime effect rather than an independent breakout edge.

### DSS-CO-001

Contraction in Uptrend remains a research-interesting phenomenon. The research-150 primary ONE_ACTIVE_PER_SYMBOL policy has OOS x2 expectancy 0.9723% and PF 1.3524, while the stricter MAX2 comparison falls to 0.4572% and PF 1.1930. The effective-sample and timing-window audits did not justify operational promotion. It is infrastructure and hypothesis material only.

### DSS-CW-001

Contraction Window was the final attempt to freeze the contraction/timing idea. DSS-004G-C closed it as timing-not-specific: placebo windows +1 and +2 beat the base, the base ranks third in the statistical family, and WRC/SPA-light rejects base-vs-family timing specificity.

## Sources

- artifacts/runtime/daily_swing/dss_pb_001_metrics.json
- artifacts/runtime/daily_swing/dss_004_decision.json
- artifacts/runtime/daily_swing/dss_bo_001_metrics.json
- artifacts/runtime/daily_swing/dss_004c_a_decision.json
- artifacts/runtime/daily_swing/dss_004c_a_matched_baselines.csv
- artifacts/runtime/daily_swing/dss_004c_a_placebo_oos.csv
- artifacts/runtime/daily_swing/dss_004e_dss_co_001_metrics.json
- artifacts/runtime/daily_swing/dss_004e_decision.json
- artifacts/runtime/daily_swing/dss_004f_r_decision.json
- artifacts/runtime/daily_swing/dss_cw_001_metrics.json
- artifacts/runtime/daily_swing/dss_004g_c_decision.json
- artifacts/runtime/daily_swing/dss_004g_c_fdr_results.csv
- artifacts/runtime/daily_swing/dss_004g_c_fdr_summary.json
- artifacts/runtime/daily_swing/dss_004g_c_wrc_spa_light.json
- artifacts/runtime/daily_swing/dss_004g_c_timing_verdict.json
