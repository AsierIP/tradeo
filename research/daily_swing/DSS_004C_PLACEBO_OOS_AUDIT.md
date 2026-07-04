# DSS-004C Placebo OOS Audit

Partial decision: `PLACEBO_TIMING_WINDOW_WARNING`

## Result

The base DSS-BO-001 signal remains better than all tested signal-shift placebos in OOS, but the degradation is not large enough to call the trigger fully specific.

| Variant | OOS trades | OOS expectancy x2 | OOS PF x2 | Delta expectancy vs base | Delta PF vs base |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | 226 | 1.8694% | 1.5363 | n/a | n/a |
| +1 day | 226 | 1.8339% | 1.5331 | 0.0356 | 0.0031 |
| +2 days | 226 | 1.4063% | 1.4027 | 0.4631 | 0.1336 |
| +3 days | 226 | 1.3312% | 1.4051 | 0.5382 | 0.1312 |
| +5 days | 222 | 1.6794% | 1.4919 | 0.1900 | 0.0444 |
| +10 days | 221 | 1.3563% | 1.3489 | 0.5132 | 0.1873 |

## Interpretation

The +1 and +5 shifts are still close to the base. That means the edge is not a one-day breakout-only impulse. It behaves more like a post-breakout momentum window. This is not a fail, because all placebos trail the base, but it blocks a clean specificity pass.
