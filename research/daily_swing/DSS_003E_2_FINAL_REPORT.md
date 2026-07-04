# DSS-003E-2 Final Report

Decision: BLOCKED_IBKR_CONNECTION

## A. Resumen ejecutivo

DSS-003E-2 queda bloqueada antes de descargar batches. TCP a IB Gateway Paper 4002 esta OK desde host y Docker, y los puertos live estan bloqueados por guard, pero los canaries historicos SPY 5D y AAON 5D fallaron por TimeoutError de conexion API. Por regla de Direccion, no se ejecuto cache research-150.

## B. Path real usado

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`

## C. Rama, commit y push

Rama: `feature/daily-swing-paper-probe-001`.

Commits:

- `f22b238 docs(daily): record DSS-003E-2 canary block`.
- Follow-up finalization commit for this report section.

Push: OK a `origin/feature/daily-swing-paper-probe-001`.

## D. Preflight IBKR 4002 y canary

- `127.0.0.1:4002`: TCP_OK, IB_GATEWAY_PAPER.
- Docker `host.docker.internal:4002`: TCP_OK, IB_GATEWAY_PAPER.
- `4001` y `7496`: bloqueados por diagnostic guard como LIVE_PORT_RISK; no usados.
- SPY 5D: FAILED, historical_data_ok=false, TimeoutError/API connection failed.
- AAON 5D: FAILED, historical_data_ok=false, TimeoutError/API connection failed.

## E. Batch plan

Research universe validado reutilizado desde DSS-003E:

- 150 acciones operativas.
- SPY/QQQ benchmark-only, operational_eligible=false.
- Sin ETFs/ETPs/funds operativos segun gate previo.

Cache research existente: 10 CSV del mini batch DSS-003E-R: AAON, AAPL, AEO, ALGM, APPF, AX, BROS, MSFT, QQQ, SPY.

No se ejecuto batch plan porque el canary bloqueo antes.

## F. Cache research

- fetched: 0.
- skipped: 0.
- failed: 0.
- quarantined: 0.
- batch_runs: 0.

## G. Simbolos fallidos/quarantined

Ningun simbolo fue descargado ni quarantined en DSS-003E-2. Canaries fallidos: SPY y AAON.

## H. Quality gate research

No ejecutado en DSS-003E-2 porque no hubo cache batch nuevo. La quality del mini batch DSS-003E-R queda como ultimo dato conocido, no como PASS research-150.

## I. operational_ready y benchmark_ready

DSS-003E-2 no recalculo quality research-150.

Ultimo dato conocido DSS-003E-R mini batch:

- operational_ready: 8.
- benchmark_ready: 2.

## J. Confirmacion 2026-07-03 sin barra fake

No se generaron datos nuevos. Ultimo dato conocido DSS-003E-R mini batch: `false_bar_2026_07_03_present=false`.

## K. Confirmacion last_valid_bar_date

No se generaron datos nuevos. Ultimo dato conocido DSS-003E-R mini batch: `last_valid_bar_date=2026-07-02`.

## L. Seguridad

Confirmado: no ordenes, no live, no paper execution, no paper orders, no backtest, no senales, no preview operativo, no cron, no `.env` real modificado, no merge, no PR nuevo, no gh.

## M. Decision DSS-003E-2

BLOCKED_IBKR_CONNECTION.

## N. Siguiente fase recomendada

Accion minima: restaurar/verificar la sesion API de IB Gateway Paper 4002 hasta que SPY 5D y AAON 5D pasen en read-only. Luego repetir DSS-003E-2 desde preflight y continuar con batches pequenos con resume/quarantine/caps. No ejecutar DSS-004E hasta que research-150 pase quality gate.
