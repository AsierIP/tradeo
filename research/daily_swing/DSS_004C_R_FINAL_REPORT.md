# DSS-004C-R Final Report

## A. Resumen ejecutivo

DSS-004C-R reconciled the DSS-004C vs DSS-004C-A baseline discrepancy cache-only. The discrepancy is methodological: DSS-004C used a coarse yearly sampler, while DSS-004C-A used exact DSS-BO-001 symbol-year counts. Under the exact matched-sample definition, CONTRACTION_ONLY beats DSS-BO-001. Decision: `DSS_BO_001_BASELINE_EXPLAINED_CONFIRMED`.

## B. Path real usado

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`

## C. Rama, commit y push si aplica

Branch: `feature/daily-swing-paper-probe-001`.

Commit/push: recorded in final chat after validation.

## D. Inventario de artefactos 004C/004C-A y untracked

Tracked DSS-004C artifacts/code/reports came from commit `713aa18`.
Tracked DSS-004C-A artifacts/code/reports came from commit `2886dad`.

New DSS-004C-R files created for this task:

- `backend/tradeo/modules/daily_swing/dss_004c_r.py`
- `backend/tradeo/tests/test_daily_swing_dss_004c_r.py`
- `scripts/run_daily_swing_dss_004c_r.py`
- `research/daily_swing/DSS_004C_R_*.md`
- `artifacts/runtime/daily_swing/dss_004c_r_*.json`
- `artifacts/runtime/daily_swing/dss_004c_r_side_by_side_baselines.csv`

No deletes.

## E. Diferencia metodologica encontrada

DSS-004C sampled matched baselines with an approximate year-level count divided across symbols. DSS-004C-A sampled candidates by exact DSS-BO-001 symbol-year counts before constructing non-overlapping trades. Signal timing, costs, holding period, and baseline names are otherwise aligned.

This makes the DSS-004C matched-baseline interpretation non-comparable with DSS-004C-A.

## F. Recompute side-by-side: unmatched vs matched

| Mode | Variant | OOS trades | Symbols | OOS exp x2 | OOS PF x2 |
|---|---|---:|---:|---:|---:|
| UNMATCHED_ALL_EVENTS | DSS_BO_001_BASE | 226 | 49 | 1.8694% | 1.5363 |
| UNMATCHED_ALL_EVENTS | TREND_ONLY | 736 | 50 | 0.4001% | 1.0901 |
| UNMATCHED_ALL_EVENTS | BREAKOUT_ONLY | 365 | 50 | 1.1457% | 1.2899 |
| UNMATCHED_ALL_EVENTS | CONTRACTION_ONLY | 423 | 49 | 1.7851% | 1.5031 |
| UNMATCHED_ALL_EVENTS | RANDOM_MATCHED | 736 | 50 | 0.4001% | 1.0901 |
| MATCHED_SAMPLE | DSS_BO_001_BASE | 226 | 49 | 1.8694% | 1.5363 |
| MATCHED_SAMPLE | TREND_ONLY | 225 | 49 | 1.3024% | 1.3712 |
| MATCHED_SAMPLE | BREAKOUT_ONLY | 196 | 49 | 1.8215% | 1.5129 |
| MATCHED_SAMPLE | CONTRACTION_ONLY | 206 | 49 | 2.7408% | 1.9379 |
| MATCHED_SAMPLE | RANDOM_MATCHED | 185 | 49 | 1.0225% | 1.2427 |

Exact matched mode confirms DSS-004C-A: CONTRACTION_ONLY explains more of the edge than DSS-BO-001.

## G. Guard audit

PASS. SPY/QQQ are excluded from trades, fake 2026-07-03 is absent, last_valid_bar_date is 2026-07-02, signal is at t, entry is t+1 next open, high20 is prior high20, ATR contraction uses t-1, costs are x2 20 bps, and the run is cache-only.

## H. Decision DSS-004C-R

`DSS_BO_001_BASELINE_EXPLAINED_CONFIRMED`

## I. Validos e invalidados

Valid:

- DSS-BO-001 base metrics.
- DSS-004C-A exact symbol-year matched recompute evidence.
- DSS-004C-R side-by-side recompute and guard audit.

Invalidated:

- DSS-004C coarse matched-baseline interpretation as a comparable matched baseline.

## J. Confirmacion seguridad

No ordenes, no paper orders, no live, no paper execution, no cron, no preview operativo, no senales operativas, no merge.

## K. Siguiente fase recomendada

Director decision. If continuing, audit CONTRACTION_ONLY as a separate honest candidate, provisionally DSS-CO-001. Do not execute it yet.
