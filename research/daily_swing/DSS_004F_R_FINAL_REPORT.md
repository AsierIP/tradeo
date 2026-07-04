# DSS-004F-R Final Report

## A. Resumen ejecutivo

DSS-004F-R reconciliado. El rerun determinístico coincide con `Reporte B` y con los artefactos de `948410e`, no con `Reporte A`. La conclusión conceptual se mantiene: `TIMING_WINDOW_CONFIRMED`, pero el canónico debe llevar `EFFECTIVE_SAMPLE_WARNING` por bootstrap symbol p05 negativo.

## B. Path real usado

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`

## C. Rama, commit y push si aplica

Rama: `feature/daily-swing-paper-probe-001`. HEAD inicial: `948410ecd8a2b323e956694e496e58cf1233032a`. DSS-004F-R genera reportes/artefactos nuevos y requiere commit correctivo.

## D. Inventario de artefactos y git hygiene

`948410e` contiene los artefactos DSS-004F base. No había cambios tracked antes de la tarea. Los nuevos artefactos `dss_004f_r_*` están en `artifacts/runtime/daily_swing/`; como `artifacts/` está ignorado, deben force-add si se commitean.

## E. Rerun determinístico

Coincide con `Reporte B` / commit `948410e`. No coincide con `Reporte A`.

## F. Root cause de la discrepancia

`Reporte A` usó EPISODE_GAP_5 por huecos de días calendario <= 5 y 100 iteraciones bootstrap. El código committeado usa huecos de sesiones de mercado por `signal_idx` <= 5 y 20 iteraciones por defecto. Los fines de semana/calendario dividen más episodios en Reporte A.

## G. Cifras canónicas DSS-004F

Raw signals total/OOS: `15119` / `9488`.

EPISODE_GAP_5 episodes total/OOS: `1394` / `847`.

Raw signals per episode mean/median/p95: `10.8458` / `6.0000` / `40.0000`.

| Offset | OOS episodes | OOS symbols | Exp x2 | PF x2 |
|---:|---:|---:|---:|---:|
| 0 | 843 | 147 | 0.7336 | 1.2516 |
| 1 | 841 | 147 | 1.0653 | 1.3720 |
| 2 | 838 | 147 | 0.9730 | 1.3454 |
| 5 | 832 | 147 | 0.9861 | 1.3524 |
| 10 | 825 | 147 | 0.8648 | 1.3000 |

Bootstrap seed/iterations: `40406` / `20`. Symbol expectancy p05/p50/p95: `-0.0316` / `0.9166` / `1.3883`.

## H. Guard reconfirmation

PASS: cache research-150, SPY/QQQ excluidos, fake 2026-07-03 ausente, last_valid_bar_date `2026-07-02`, señal `t`, entrada `t+1` u offset relativo, ATR rank `t-1`, sin IBKR y sin descargas.

## I. Artefactos válidos e invalidados/superseded

Válidos/canónicos: `DSS_004F_R_*`, `dss_004f_r_*`, y los artefactos base de `948410e` cuando se leen como Reporte B.

Superseded: métricas de `Reporte A` en chat, por agrupación calendario y bootstrap 100 no canónicos para el commit actual.

## J. Seguridad

Confirmado: no órdenes, no paper orders, no live, no paper execution, no preview operativo, no señales operativas, no IBKR, no descargas, no cron, no .env real, no merge, no PR.

## K. Decisión DSS-004F-R

`DSS_004F_CANONICAL_EFFECTIVE_SAMPLE_WARNING`

## L. Siguiente fase recomendada

Dirección puede diseñar DSS-CW-001 en una tarea separada. No iniciarlo desde DSS-004F-R.
