# DSS-ROADMAP-001 Final Report

Task: T-DAILY-ROADMAP-001
Generated: 2026-07-05

## A. Resumen ejecutivo

T-DAILY-ROADMAP-001 completada como tarea documentation-only. La linea Daily PB/BO/CO/CW queda cerrada; no se rescata ningun patron y no se crea DSS-005. Se evaluaron seis search-spaces candidatos y se selecciona una unica recomendacion: `Gap continuation / gap reversal`, porque aprovecha la infraestructura Daily actual, no exige datos externos para el primer protocolo y permite una pre-registracion estricta antes de cualquier backtest.

Decision roadmap: `NEXT_DAILY_SEARCHSPACE_SELECTED`.

## B. Path real usado

`/tmp/tradeo-main-004k-clean`

## C. Rama creada y commit/push si aplica

Rama: `feature/daily-roadmap-next-searchspace-001`

Esta rama contiene solo documentacion y un CSV/JSON de decision de roadmap. No toca codigo, tests, configuracion, runtime artifacts, datos, memoria ni paper/live surfaces.

## D. Terminal findings summary

Ver `research/daily_swing/DSS_ROADMAP_001_TERMINAL_FINDINGS.md`.

Resumen:

- DSS-PB-001: research fail despues de OOS/cost review; no shadow/paper/live.
- DSS-BO-001: baseline explained fail; no especificidad de breakout.
- DSS-CO-001: timing/effective-sample warning; no candidato operativo.
- DSS-CW-001: timing not specific fail; placebos de timing dominan.

Conclusiones: PB/BO/CO/CW no avanzan y no deben rescatarse como DSS-005.

## E. Infra capability map

Ver `research/daily_swing/DSS_ROADMAP_001_INFRA_CAPABILITY_MAP.md`.

La infraestructura reusable cubre:

- Daily OHLCV cache/read-only tooling.
- Quality gates de OHLCV/universo.
- Backtests cache-only PB/BO/CO/CW.
- No-lookahead guards.
- Cost/OOS metrics.
- Baseline/placebo/timing/concentration audits.
- FDR/WRC/SPA-light aproximado.
- Diagnosticos IBKR read-only, no usados en esta tarea.
- Tests focales Daily.

La infraestructura encaja mejor con search-spaces stock-only y Daily-bar sin datos externos nuevos.

## F. Search-space matrix

Ver:

- `research/daily_swing/DSS_ROADMAP_001_SEARCH_SPACE_MATRIX.md`
- `research/daily_swing/dss_roadmap_001_search_space_matrix.csv`

Ranking operativo:

1. Gap continuation / gap reversal: recomendado.
2. Earnings / post-earnings drift: alto valor, bloqueado por decision de datos timestamped.
3. Sector / relative strength: diferir hasta tener clasificacion sectorial point-in-time.
4. Market breadth + pullback: diferir hasta politica de breadth data.
5. ETF/macro separado: requiere decision explicita de politica `etf_macro`.
6. Daily-to-intraday hybrid entry: diferir hasta que exista edge Daily-only.

## G. Recomendacion prioritaria

Seleccionar `Gap continuation / gap reversal`.

Motivo:

- Usa OHLCV Daily existente.
- No requiere earnings calendar, breadth data ni clasificacion sectorial externa para una primera pre-registracion.
- Es auditable con open/close/high/low y no es un rescate de PB/BO/CO/CW.
- Permite adversarial tests claros: adverse open slippage, next-close placebo, delayed entry, threshold perturbation, direction placebo y matched random event days.

## H. Pre-registration draft summary

Ver `research/daily_swing/DSS_ROADMAP_001_PREREGISTRATION_DRAFT.md`.

El draft define:

- Hipotesis de gap continuation/reversal.
- Universo stock-only con SPY/QQQ benchmark-only.
- Datos Daily OHLCV existentes.
- Estructura preliminar de gap size, direction, filters, entry/exit.
- Split IS/OOS, costes x1/x2/x3 y adverse open slippage.
- Placebos/adversarial y rejection gates.
- Bloqueo explicito de paper hasta aprobacion separada.

## I. Decision roadmap

`NEXT_DAILY_SEARCHSPACE_SELECTED`

Search-space seleccionado: `gap_continuation_gap_reversal`

Siguiente task sugerida: `T-DAILY-GAP-001-PROTOCOL`.

La siguiente tarea debe pre-registrar umbrales, variantes, splits, costes, slippage adverso y criterios de rechazo. No debe ejecutar backtest salvo autorizacion explicita nueva.

## J. Confirmacion seguridad

No ordenes. No paper orders. No live orders. No ejecucion paper. No preview operativo. No senales operativas. No backtest. No IBKR. No descargas de datos. No cron. No `.env` real. No gates relajados. No scoring operativo. No DSS-005. No rescate PB/BO/CO/CW. No `gh`. No merge. No push a main. No rama contaminada.

## K. Siguiente tarea recomendada

T-DAILY-GAP-001-PROTOCOL - Pre-registrar el protocolo exacto de gap continuation/reversal con thresholds, variantes, split IS/OOS, costes, adverse open slippage, placebos, baselines, criterios de rechazo y criterios `research_pass`. Mantener paper/live bloqueados.
