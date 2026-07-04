# DSS-004C Matched Baselines

Partial decision: `BASELINE_WARNING`

## Result

| Variant | OOS trades | OOS symbols | OOS expectancy x2 | OOS PF x2 | Last 12m expectancy | Last 24m expectancy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DSS_BO_001_BASE | 226 | 49 | 1.8694% | 1.5363 | 1.3401% | 1.0726% |
| TREND_ONLY | 177 | 50 | 0.4343% | 1.1094 | 1.2946% | -0.1273% |
| BREAKOUT_ONLY | 162 | 50 | -0.6903% | 0.8411 | -0.3993% | -1.0358% |
| CONTRACTION_ONLY | 164 | 49 | 1.6253% | 1.4344 | 0.9276% | 0.9524% |
| RANDOM_MATCHED | 168 | 48 | -0.7872% | 0.8187 | -1.4716% | -0.6285% |

## Interpretation

The base beats trend-only, breakout-only, and random matched. The warning comes from contraction-only, which is close enough to suggest a substantial part of the edge may be volatility-compression plus trend, not the breakout trigger alone.

This does not explain the edge completely, but it prevents promoting DSS-BO-001 as a clean independent breakout pattern on the 50-symbol pilot only.
