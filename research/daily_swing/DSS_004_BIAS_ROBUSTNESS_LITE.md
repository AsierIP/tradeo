# DSS-004 Bias and Robustness Lite

Bias decision: `BIAS_WARNING`.

## Audits

- Lookahead audit: `PASS_SIGNAL_T_ENTRY_T_PLUS_1`
- Leakage audit: `PASS_CACHE_ONLY_NO_FUTURE_SIGNAL_FIELDS`
- Duplicate trades audit: `PASS`
- Holiday audit: `PASS_NO_2026_07_03_BAR`
- FDR/WRC/SPA: not implemented; this blocks live promotion, not this research-only paper probe decision.

## Variants

| Variant | Trades | Expectancy % | PF |
|---|---:|---:|---:|
| Base next open | 925 | 0.3522 | 1.1199 |
| Entry next close | 925 | 0.3812 | 1.1408 |
| Next open adverse 10 bps | 925 | 0.2522 | 1.0844 |
| Placebo signal +1 | 922 | 0.4385 | 1.1518 |
| Placebo signal +2 | 918 | 0.4093 | 1.1453 |
| Placebo signal +5 | 917 | -0.0405 | 0.9867 |

The placebo and entry sensitivity results do not rescue the OOS failure. The base research decision remains fail.

Artifact: `artifacts/runtime/daily_swing/dss_004_bias_robustness.json`.
