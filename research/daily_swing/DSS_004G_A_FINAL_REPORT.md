# DSS-004G-A Final Report

## A. Resumen ejecutivo

DSS-004G-A completada como diseno cientifico previo. No se ejecuto backtest nuevo, no se generaron senales, no hubo preview, no paper, no live, no IBKR y no ordenes. La tarea deja preparado un protocolo honesto para `DSS-CW-001 Contraction Window` basado solo en cifras canonicas `DSS-004F-R`.

Decision: `DSS_CW_001_SPEC_READY_FOR_RESEARCH_BACKTEST`.

## B. Path real usado

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`

## C. Rama, commit y push si aplica

Rama: `feature/daily-swing-paper-probe-001`.

Commit/push: pendiente en el momento de generar este reporte.

## D. Sintesis canonica usada

Inputs canonicos:

- `DSS-004E`: `DSS_CO_001_RESEARCH_WARNING_RESEARCH150`.
- `DSS-004F-R`: `DSS_004F_CANONICAL_EFFECTIVE_SAMPLE_WARNING`.
- Reporte A queda superseded.
- Artefactos validos: `DSS_004F_R_*`, `dss_004f_r_*`, y `948410e` leido como Reporte B.

Cifras base usadas:

- Raw signals total/OOS: `15119` / `9488`.
- EPISODE_GAP_5 episodes total/OOS: `1394` / `847`.
- Offset 0 OOS x2: `0.7336%`, PF `1.2516`.
- Offset +1 OOS x2: `1.0653%`, PF `1.3720`.
- Offset +2 OOS x2: `0.9730%`, PF `1.3454`.
- Offset +5 OOS x2: `0.9861%`, PF `1.3524`.
- Offset +10 OOS x2: `0.8648%`, PF `1.3000`.
- Bootstrap symbol p05/p50/p95 expectancy: `-0.0316` / `0.9166` / `1.3883`.

Interpretacion: hay ventana temporal; no hay aprobacion de senal puntual `DSS-CO-001`.

## E. Especificacion draft DSS-CW-001

`DSS-CW-001` queda definido como candidato de ventana, no como offset ganador. La propuesta base:

- Universo research-150 operational equities.
- `SPY/QQQ` solo benchmark/regime.
- Regimen: `SPY close > SMA200` o `SPY return20d > 0`.
- Tendencia simbolo: `close > SMA50` y `close > SMA200` o `SMA50 > SMA200`.
- Contraccion: `ATR14_pct(t-1) <= p40 rolling 120d hasta t-1`.
- Episodio: `EPISODE_GAP_5` por trading-session signal index.
- Ventana: desde `first_signal_date` hasta min(`first_signal_date + 5 sesiones`, `last_signal_date`).
- Entrada futura de research: primera sesion elegible que pase filtros de cartera, no offset +1 elegido post hoc.
- Salida: close tras 10 sesiones.
- Politica: one active per symbol y max 2 new episodes per day.
- Prioridad: menor ATR14_pct_rank, luego fecha, luego simbolo estable.

## F. Protocolo de validacion

La validacion futura debe congelar especificacion antes de mirar OOS. Mantener IS hasta `2024-12-31` y OOS desde `2025-01-01`. Si hay variantes de ventana o gap, solo pueden calibrarse en IS o con nested calibration y correccion estadistica.

Pruebas requeridas: placebo temporal, random matched, trend-only, vol-high-only, contraction-only si queda limpio, delayed offsets como adversarial, bootstrap por symbol y symbol-month, concentracion, effective sample y FDR/WRC/SPA-light antes de paper/live.

Criterios minimos: OOS x2 > 0, PF x2 > 1.20, MAX2 PF x2 > 1.15, x3 no destruye edge, ultimos 12m no negativo, placebos no dominan, concentracion aceptable y guard sin leakage.

## G. Protocolo de operabilidad futura

Para shadow: especificacion congelada, backtest research-only, guard, bias, concentracion, bootstrap y FDR/WRC/SPA-light o blocker documentado.

Para paper_probe_candidate: autorizacion explicita de Asier, presupuesto de riesgo, paper-only check, `live_armed=false`, `paper_enabled=true` solo si se autoriza, kill-switch y telemetry.

Limites futuros: max 2 episodios nuevos/dia, one active per symbol, max open positions/position value/daily loss pendientes de aprobacion, kill-switch obligatorio.

## H. Decision DSS-004G-A

`DSS_CW_001_SPEC_READY_FOR_RESEARCH_BACKTEST`

Esto solo recomienda la siguiente microfase `DSS-004G-B`: ejecutar backtest research-only de `DSS-CW-001` segun la especificacion congelada. No lo ejecuta ni lo autoriza automaticamente.

## I. Seguridad

Confirmado: no ordenes, no paper orders, no live orders, no paper execution, no preview operativo, no senales operativas, no backtest nuevo, no IBKR, no descargas, no cron, no .env real, no relajar gates, no merge, no PR, no gh.

## J. Siguiente fase recomendada

Direccion puede autorizar una tarea separada `T-DAILY-SWING-004G-B` para ejecutar backtest research-only de `DSS-CW-001` con esta especificacion. Hasta entonces, no hay DSS-005, paper preview, senales ni ordenes.
