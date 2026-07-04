# DSS-004C-A Matched Baseline Audit

Generated: 2026-07-04

## Scope

Compare frozen DSS-BO-001 against simple matched baselines without optimization, grid search, or OOS tuning. Samples are matched by symbol/year to the base signal count when possible. RANDOM_MATCHED uses fixed seed 40401.

## Result

Partial decision: BASELINE_FAIL.

The frozen base does not clearly beat simple baselines. CONTRACTION_ONLY beats DSS-BO-001 on OOS expectancy and PF, while BREAKOUT_ONLY is very close to the base.

| Variant | Trades total | Trades OOS | Symbols OOS | OOS expectancy net x2 | OOS PF net x2 | Last 12m expectancy | Last 24m expectancy | Top 3 contribution |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSS_BO_001_BASE | 350 | 226 | 49 | 1.8694% | 1.5363 | 1.3401% | 1.0726% | 33.90% |
| TREND_ONLY | 349 | 225 | 49 | 1.3024% | 1.3712 | 1.5446% | 0.9631% | 30.89% |
| BREAKOUT_ONLY | 316 | 196 | 49 | 1.8215% | 1.5129 | 3.1052% | 1.0002% | 40.71% |
| CONTRACTION_ONLY | 323 | 206 | 49 | 2.7408% | 1.9379 | 2.0651% | 2.1346% | 27.42% |
| RANDOM_MATCHED | 287 | 185 | 49 | 1.0225% | 1.2427 | 1.6023% | 0.2589% | 33.37% |

## Interpretation

The base combination of contraction plus breakout is not yet justified as an independent pattern. The strongest explanation in this audit is that the contraction component, under the same regime/trend constraints, captures most or more of the observed OOS edge. This blocks DSS-005.

## Artifacts

- artifacts/runtime/daily_swing/dss_004c_a_matched_baselines.csv
- artifacts/runtime/daily_swing/dss_004c_a_matched_baselines_summary.json
