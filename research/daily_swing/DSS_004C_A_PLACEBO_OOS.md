# DSS-004C-A Placebo OOS Audit

Generated: 2026-07-04

## Scope

Recalculate DSS-BO-001 placebos with focus on OOS metrics, not full-sample headline metrics. This audit is cache-only and keeps the frozen DSS-BO-001 specification unchanged.

## Result

Partial decision: PLACEBO_TIMING_WINDOW_WARNING.

All tested placebos stay positive in OOS, but none matches or beats the base edge or base PF. The decay is not monotonic because +5 improves relative to +2/+3, so this does not prove tight one-day breakout specificity.

| Variant | Trades total | Trades OOS | Symbols OOS | OOS expectancy net x2 | OOS PF net x2 | Top 3 contribution | Base edge minus variant |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DSS_BO_001_BASE | 350 | 226 | 49 | 1.8694% | 1.5363 | 33.90% | n/a |
| PLACEBO_SHIFT_PLUS_1 | 350 | 226 | 49 | 1.8339% | 1.5331 | 38.07% | 0.0356 |
| PLACEBO_SHIFT_PLUS_2 | 350 | 226 | 49 | 1.4063% | 1.4027 | 39.61% | 0.4631 |
| PLACEBO_SHIFT_PLUS_3 | 350 | 226 | 49 | 1.3312% | 1.4051 | 33.75% | 0.5382 |
| PLACEBO_SHIFT_PLUS_5 | 346 | 222 | 49 | 1.6794% | 1.4919 | 28.12% | 0.1900 |
| PLACEBO_SHIFT_PLUS_10 | 345 | 221 | 49 | 1.3563% | 1.3489 | 40.13% | 0.5132 |

## Interpretation

The base signal is better than every shifted placebo, but +1 and +5 remain close enough to imply a timing window rather than a highly specific close_t breakout trigger. This supports continued caution before any DSS-005 paper-preview phase.

## Artifacts

- artifacts/runtime/daily_swing/dss_004c_a_placebo_oos.csv
- artifacts/runtime/daily_swing/dss_004c_a_placebo_oos_summary.json
