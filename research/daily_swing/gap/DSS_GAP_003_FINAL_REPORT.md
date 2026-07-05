# DSS-GAP-003 Final Report

## A. Resumen ejecutivo

T-DAILY-GAP-003 queda completada como diseno y validacion de matriz solamente. Se
creo una matriz cerrada machine-readable para un futuro dry-run cache-only de gap
continuation/reversal. No se ejecuto backtest, no se calculo edge, no se eligio mejor
threshold, no se generaron senales, no se creo preview, no se uso IBKR y no se
descargaron datos.

Decision: GAP_BACKTEST_MATRIX_READY_FOR_CACHE_ONLY_DRY_RUN.

## B. Path real usado

`/tmp/tradeo-main-004k-clean`

## C. Rama y commit/push

Rama: `feature/daily-gap-protocol-001`.

Commit/push: esta entrega queda en el commit Git de cierre `feat(daily): preregister
gap backtest matrix`, push OK a `origin/feature/daily-gap-protocol-001`.

## D. Contexto GAP-001/GAP-002A usado

Se usaron las especificaciones GAP-001 y summaries GAP-002A bajo
`research/daily_swing/gap`. El ledger runtime solo queda autorizado para schema/columnas
en esta fase; GAP-003 no mira rentabilidad.

Estado aceptado desde GAP-002A:

- ledger local runtime con 114304 filas;
- 152 simbolos totales;
- 150 simbolos operativos;
- 54942 eventos ready;
- fecha 2023-07-05 a 2026-07-02;
- `NO_LOOKAHEAD_PASS`.

## E. Matrix summary

Artifacts:

- `research/daily_swing/gap/DSS_GAP_003_BACKTEST_MATRIX.md`
- `research/daily_swing/gap/dss_gap_003_backtest_matrix.csv`
- `research/daily_swing/gap/dss_gap_003_backtest_matrix.json`

Resumen:

- 92 filas totales.
- 40 candidate tests, cap maximo 40.
- 8 filas baseline, 16 filas placebo y 28 filas de diseno bloqueado para filtros/policies.
- Familias: same-day continuation, same-day reversal, next-day continuation,
  next-day reversal.
- Policies: `ALL_EVENTS_RESEARCH_ONLY`, `ONE_ACTIVE_PER_SYMBOL`,
  `MAX_2_NEW_TRADES_PER_DAY`.
- Baselines/placebos: `MATCHED_NON_GAP`, `RANDOM_MATCHED`, `SIGN_INVERTED_GAP`,
  `DELAYED_ENTRY`, `THRESHOLD_PERTURBATION`, `EARNINGS_SENSITIVITY`.

## F. No-lookahead matrix audit

Decision parcial: MATRIX_NO_LOOKAHEAD_PASS.

Same-day decide en `open_t` y no usa `high_t`, `low_t`, `close_t`, `volume_t`,
`gap_fill_ratio` ni outcomes para decidir. Next-day decide after `close_t` y puede usar
OHLCV completo de t antes de `open_t_plus_1`. SPY/QQQ quedan solo para
benchmark/regime.

## G. Validation scaffold

Se creo:

- `backend/tradeo/modules/daily_swing/gap_backtest_matrix.py`
- `scripts/validate_daily_gap_backtest_matrix.py`
- `backend/tradeo/tests/test_daily_gap_backtest_matrix.py`

El scaffold valida schema, duplicate `test_id`, flags de seguridad, campos
permitidos/prohibidos, cap de candidate tests y existencia de baselines/placebos. El
script rechaza modos execution/orders/signals/preview/paper/live/IBKR.

## H. Tests/validaciones

- `python3 -m py_compile scripts/validate_daily_gap_backtest_matrix.py backend/tradeo/modules/daily_swing/gap_backtest_matrix.py` => exit 0.
- `python3 scripts/validate_daily_gap_backtest_matrix.py --write-default --output-dir research/daily_swing/gap` => exit 0.
- `docker run ... pytest -q tradeo/tests/test_daily_gap_backtest_matrix.py tradeo/tests/test_daily_gap_protocol.py tradeo/tests/test_daily_gap_event_ledger.py` => 29 passed.
- `docker run ... ruff check tradeo/modules/daily_swing/gap_backtest_matrix.py tradeo/tests/test_daily_gap_backtest_matrix.py ../scripts/validate_daily_gap_backtest_matrix.py` => exit 0.
- `git diff --check` => exit 0.
- `docker build -f backend/Dockerfile -t tradeo-backend-gap003-test .` => bloqueado antes de construir por Docker/buildx local: `no space left on device` en `/home/vboxuser/.docker/buildx/activity`.

## I. Decision GAP-003

GAP_BACKTEST_MATRIX_READY_FOR_CACHE_ONLY_DRY_RUN.

## J. Seguridad

Confirmado: no ordenes, no paper, no live, no preview, no senales, no backtest, no
IBKR, no descargas, no cron, no gh, no merge, no push a main, no DSS-005, no rescate
PB/BO/CO/CW, no `.env` real modificado y no artifacts runtime versionados.

## K. Siguiente tarea recomendada

T-DAILY-GAP-004 - Cache-only dry-run of gap backtest matrix, no candidate approval.

No ejecutarla sin nueva autorizacion explicita de Direccion.
