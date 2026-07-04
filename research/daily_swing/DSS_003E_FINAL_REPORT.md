# DSS-003E Final Report

Task: T-DAILY-SWING-003E

Decision: BLOCKED_IBKR

## A. Resumen ejecutivo

DSS-003E no queda lista para DSS-004E. El preflight TCP de IBKR Paper 4002 paso y el universo research-150 es valido, pero la conexion API de IBKR timeout repetidamente al intentar cachear el primer simbolo. Se paro de forma segura para evitar reintentos agresivos. No se ejecuto backtest ni se generaron senales.

## B. Path real usado

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`

## C. Rama, commit y push

Rama: `feature/daily-swing-paper-probe-001`.

Commit/push: pendiente en esta ejecucion hasta validar artefactos y reporte.

## D. Preflight IBKR 4002

PREFLIGHT_PASS:

- 127.0.0.1:4002 TCP_OK.
- host.docker.internal:4002 desde Docker TCP_OK.
- Clasificacion: IB_GATEWAY_PAPER.
- read_only=true.
- Puertos live 7496/4001 no usados.

## E. Universo research validado

RESEARCH_UNIVERSE_PASS:

- 150 acciones operativas.
- SPY/QQQ incluidos solo benchmark_only.
- Sin duplicados.
- Sin ETFs/ETPs/funds operativos.
- Sin product_type unknown operativo.

## F. Cache research

BLOCKED_IBKR_TIMEOUT:

- fetched: 0.
- skipped: 0.
- failed: 1.
- Primer simbolo: AAON.
- Error: TimeoutError en conexion API IBKR.

## G. Simbolos fallidos

AAON fallo por timeout de conexion API. No se continuo el universo para evitar bucles agresivos.

## H. Quality gate research

BLOCKED_MIN_READY:

- operational_ready: 0.
- benchmark_ready: 0.
- data_gate: BLOCKED.

## I. operational_ready y benchmark_ready

operational_ready=0, benchmark_ready=0.

## J. 2026-07-03 sin barra fake

Confirmado en el resumen de quality: false_bar_2026_07_03_present=false.

## K. last_valid_bar_date

Confirmado: last_valid_bar_date=2026-07-02.

## L. Seguridad

Confirmado: no ordenes, no live, no paper execution, no backtest, no senales, no preview operativo, no cron, no .env real modificado, no merge, no PR.

## M. Decision DSS-003E

BLOCKED_IBKR.

## N. Siguiente fase recomendada

Restaurar/verificar sesion API de IBKR Paper en puerto 4002 y repetir DSS-003E con `--resume`. No ejecutar DSS-004E hasta que la cache research y el quality gate pasen.
