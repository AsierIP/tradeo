# DSS-004G-A Canonical Synthesis

## Scope

This document freezes the canonical input for `DSS-CW-001 Contraction Window` design. It does not execute a new backtest, does not generate operational signals, and does not change `DSS-CO-001`.

## Canonical Inputs

- `DSS-003E-4`: `DATA_GATE_RESEARCH_PASS`.
- `DSS-004E`: `DSS_CO_001_RESEARCH_WARNING_RESEARCH150`.
- `DSS-004F-R`: `DSS_004F_CANONICAL_EFFECTIVE_SAMPLE_WARNING`.
- Canonical report source: `DSS_004F_R_*` plus `dss_004f_r_*`, and the `948410e` DSS-004F artifacts when read as Report B.
- Superseded source: Report A chat metrics using calendar-day episode grouping and 100 bootstrap iterations.

## What Survived

`DSS-CO-001` still finds a positive contraction-in-uptrend phenomenon on research-150, and the result is not explained only by concentration. On `DSS-004E`, `ONE_ACTIVE_PER_SYMBOL` OOS net x2 expectancy was `0.9723%` with PF `1.3524` across `147` OOS symbols. The `MAX_2_NEW_TRADES_PER_DAY_SIM` policy stayed positive with OOS net x2 expectancy `0.4572%` and PF `1.1930`.

`DSS-004F-R` confirms this is better described as a timing window than as a precise point-entry signal. Canonical EPISODE_GAP_5 counts are `1394` total episodes and `847` OOS episodes. Offset OOS x2 metrics remain positive for 0, +1, +2, +5, and +10 sessions.

## What Failed

The base `DSS-CO-001` entry does not dominate delayed timing. In `DSS-004E`, placebo shifts +1, +2, +5, and +10 matched or beat the base. In `DSS-004F-R`, episodic offsets also show delayed entries staying positive and often stronger than offset 0:

| Offset | OOS episodes | OOS symbols | Exp x2 | PF x2 |
|---:|---:|---:|---:|---:|
| 0 | 843 | 147 | 0.7336 | 1.2516 |
| 1 | 841 | 147 | 1.0653 | 1.3720 |
| 2 | 838 | 147 | 0.9730 | 1.3454 |
| 5 | 832 | 147 | 0.9861 | 1.3524 |
| 10 | 825 | 147 | 0.8648 | 1.3000 |

The canonical symbol bootstrap also has a slightly negative p05 expectancy: `-0.0316`, with p50 `0.9166` and p95 `1.3883`. That keeps the result in warning, not pass.

## Canonical Uncertainties

- Exact timing remains unresolved; delayed offsets are evidence of a broad window, not candidates to pick post hoc.
- Effective sample is smaller than raw trade counts suggest because episodes cluster heavily.
- Bootstrap p05 is slightly negative at symbol level.
- FDR/WRC/SPA remains a required future gap before live or paper approval.
- Drawdown still needs a portfolio-normalized treatment for any future candidate.
- `DSS-CW-001` must be specified before testing to avoid rebranding the +1 offset as an optimized strategy.

## Decision For This Input Layer

Use only the canonical `DSS-004F-R` figures above for `DSS-CW-001` design. Do not use Report A metrics.
