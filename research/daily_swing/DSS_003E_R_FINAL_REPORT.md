# DSS-003E-R Final Report

Decision: RESEARCH_RESUME_READY_SMALL_BATCHES

## A. Resumen ejecutivo

DSS-003E-R resolvio el bloqueo a una causa accionable. El historical canary ya responde para SPY, AAON y AAPL, incluido AAON 3Y, por lo que el timeout previo no parece un problema fijo de AAON ni de permisos de market data. El problema era una combinacion de inestabilidad transitoria IBKR/API y un loader demasiado poco defensivo. Se aplico patch de resume seguro y un mini-batch de 10 simbolos paso cache + quality.

No se ejecuto DSS-004E. No hubo backtest, senales, preview operativo, paper execution ni live.

## B. Path real usado

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`

## C. Rama, commit y push

Rama: `feature/daily-swing-paper-probe-001`.

Commit/push: pendiente al cierre de este reporte; ejecutar tras validacion final si el diff queda limpio.

## D. Canary probes

- TCP `127.0.0.1:4002`: TCP_OK, IB_GATEWAY_PAPER.
- TCP Docker `host.docker.internal:4002`: TCP_OK, IB_GATEWAY_PAPER.
- SPY 5D: OK, 5 barras.
- SPY 1M: OK, 501 barras.
- AAON 5D: OK, 5 barras.
- AAON 1M: OK, 501 barras.
- AAON 3Y: OK, 752 barras.
- AAPL 3Y: OK, 752 barras.

## E. Clasificacion del timeout

HISTORICAL_FARM_OK en el momento de DSS-003E-R. El timeout anterior queda clasificado como transitorio/API-session instability, no como AAON-only, no como long-duration-only y no como market-data permission.

## F. Loader audit

`skipped=0` en DSS-003E se explica porque DSS-003E uso `daily_ohlcv_research`, mientras la cache pilot existente estaba en `daily_ohlcv`.

El loader antes no tenia controles suficientes de timeout/retry/quarantine/max-fetch. Ahora el manifest registra intentos y errores por simbolo y puede parar por benchmark, timeout consecutivo o cap de nuevos fetches.

## G. Patch aplicado

Patch aplicado a:
- `backend/tradeo/modules/daily_swing/dss_003.py`
- `backend/tradeo/services/ibkr_data_provider.py`
- `scripts/cache_daily_ohlcv.py`
- `scripts/probe_ibkr_historical_readonly.py`
- `backend/tradeo/tests/test_daily_swing_dss_003.py`

## H. Mini batch result

MINI_BATCH_OK_READY_FOR_RESEARCH_RESUME.

- Fetched: 10.
- Failed: 0.
- operational_ready: 8.
- benchmark_ready: 2.
- `false_bar_2026_07_03_present=false`.
- `last_valid_bar_date=2026-07-02`.

## I. Seguridad

Confirmado: no ordenes, no paper orders, no live, no paper execution, no backtest, no senales, no preview operativo, no cron, no `.env` real modificado, no merge, no PR, no gh.

## J. Decision DSS-003E-R

RESEARCH_RESUME_READY_SMALL_BATCHES.

## K. Siguiente fase recomendada

DSS-003E-2, solo si Direccion lo autoriza: cachear research-150 en batches de 25 o 30 con `--resume`, `--max-new-fetches`, `--max-consecutive-timeouts`, `--request-timeout`, `--retry-count`, `--quarantine-failures` y quality gate al final.

No ejecutar DSS-004E hasta que DSS-003E-2 deje research-150 listo.
