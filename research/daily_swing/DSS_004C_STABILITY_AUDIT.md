# DSS-004C Stability Audit

Partial decision: `STABILITY_PASS`

## OOS Period Stability

| Period | Trades | Expectancy x2 | Net sum |
| --- | ---: | ---: | ---: |
| 2025Q1 | 19 | -0.9644% | -18.3240 |
| 2025Q2 | 57 | 3.9920% | 227.5434 |
| 2025Q3 | 72 | 1.4992% | 107.9400 |
| 2025Q4 | 23 | -0.1861% | -4.2794 |
| 2026Q1 | 22 | 0.0224% | 0.4917 |
| 2026Q2 | 33 | 3.3068% | 109.1237 |

## Concentration Stress

| Stress | OOS expectancy x2 | OOS PF x2 | Trades | Symbols |
| --- | ---: | ---: | ---: | ---: |
| Base OOS | 1.8694% | 1.5363 | 226 | 49 |
| Ex top 1 symbol | 1.5308% | 1.4324 | 218 | 48 |
| Ex top 3 symbols | 0.9274% | 1.2569 | 203 | 46 |
| Ex top 5 trades | 1.1206% | 1.3144 | 221 | 49 |

## Interpretation

The pattern survives removing the biggest contributors. Two OOS quarters are negative, but the result is not dominated by a single symbol, a handful of trades, or one period. Sector audit is omitted because the pilot universe has no sector field.
