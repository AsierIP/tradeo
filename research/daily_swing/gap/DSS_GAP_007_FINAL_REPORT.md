# DSS-GAP-007 Final Report

## A. Resumen ejecutivo
GAP-007 ejecutado cache-only contra la matriz cerrada GAP-006. Decision: `GAP_CONFIRMATION_FAIL_OPEN_SLIPPAGE`.

La observacion OBS1 en ALL_EVENTS/ONE_ACTIVE conserva expectancy positiva a 50 bps, pero falla a 75 bps. OBS2 falla a 50 bps, y las dos politicas MAX_2_NEW_TRADES_PER_DAY quedan negativas. No hay aprobacion de candidato, no paper, no shadow, no live, no preview, no senales y no ordenes.

## B. Path real usado
`/tmp/tradeo-main-004k-clean`.

## C. Rama y commit/push si aplica
Rama: `feature/daily-gap-protocol-001`.

Commit: `bd0030c feat(daily): execute GAP-007 confirmation`.

Push: origin/feature/daily-gap-protocol-001 tras validacion final.

## D. Input integrity
`CONFIRMATORY_INPUT_PASS`.

- Matrix GAP-006 cerrada: 12 filas.
- Confirmation targets: 6.
- Observaciones permitidas: `GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL` y `GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0`.
- Ledger runtime: 114304 filas, 2023-07-05 a 2026-07-02.
- Flags execution/paper/live/preview/signals false.
- SPY/QQQ solo benchmark/regime; universo de trading stock-only.
- Runtime queda en `artifacts/runtime`.

## E. Confirmatory execution summary
- GAP006_OBS1_REFERENCE_ALL: events OOS 3495, symbols 148, x2=0.3561%, PF x2=1.237430, 50bps=0.0561%, 75bps=-0.1939%.
- GAP006_OBS1_ONE_ACTIVE: events OOS 3495, symbols 148, x2=0.3561%, PF x2=1.237430, 50bps=0.0561%, 75bps=-0.1939%.
- GAP006_OBS1_MAX2: events OOS 686, symbols 107, x2=-0.2099%, PF x2=0.878991, 50bps=-0.5099%.
- GAP006_OBS2_REFERENCE_ALL: events OOS 7362, symbols 150, x2=0.1725%, PF x2=1.145552, 50bps=-0.1275%.
- GAP006_OBS2_ONE_ACTIVE: events OOS 7362, symbols 150, x2=0.1725%, PF x2=1.145552, 50bps=-0.1275%.
- GAP006_OBS2_MAX2: events OOS 250, symbols 21, x2=-0.2116%, PF x2=0.846896, 50bps=-0.5116%.

## F. Open realism / operability / earnings review
`OPEN_REALISM_FAIL`.

Same-day open execution is not robust under the required adverse slippage and portfolio constraints. OBS2 is negative at 50 bps, both MAX2 rows are negative before and after slippage, and 75 bps destroys OBS1 too. Earnings sensitivity remains descriptive only because no timestamp-safe earnings calendar is available.

## G. Statistical / baseline / placebo verdict
`STAT_BASELINE_PASS`.

Controls do not dominate the best target in this confirmatory run. Best control is threshold perturbation at x2=0.1725% with PF x2=1.145552, below OBS1 target x2=0.3561% with PF x2=1.237430. FDR/WRC/SPA-light is `FDR_WRC_SPA_LIGHT_PASS` with min q=0.0. This does not override the open realism failure.

## H. Tests/validaciones
- `python3 -m py_compile scripts/run_daily_gap_confirmatory_matrix.py backend/tradeo/modules/daily_swing/gap_confirmatory_run.py` => exit 0.
- Host `python3 -m pytest ...` no disponible: `No module named pytest`.
- `python3 scripts/run_daily_gap_confirmatory_matrix.py --ledger artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv --matrix research/daily_swing/gap/dss_gap_006_confirmatory_matrix.json --criteria research/daily_swing/gap/DSS_GAP_006_CONFIRMATION_CRITERIA.json --output-dir artifacts/runtime/daily_swing/gap --research-output-dir research/daily_swing/gap --cache-only --no-ibkr --no-signals --no-preview --no-orders` => exit 0.
- `docker run --rm -v "$PWD":/app -w /app tradeo-backend:gap006 pytest -q backend/tradeo/tests/test_daily_gap_confirmatory_run.py backend/tradeo/tests/test_daily_gap_confirmatory_protocol.py` => 19 passed.
- `docker run --rm -v "$PWD":/app -w /app tradeo-backend:gap007 pytest -q backend/tradeo/tests/test_daily_gap_protocol.py backend/tradeo/tests/test_daily_gap_event_ledger.py backend/tradeo/tests/test_daily_gap_backtest_matrix.py backend/tradeo/tests/test_daily_gap_matrix_dry_run.py backend/tradeo/tests/test_daily_gap_confirmatory_protocol.py backend/tradeo/tests/test_daily_gap_confirmatory_run.py` => 59 passed.
- `docker run --rm -v "$PWD":/app -w /app tradeo-backend:gap006 ruff check scripts/run_daily_gap_confirmatory_matrix.py backend/tradeo/modules/daily_swing/gap_confirmatory_run.py backend/tradeo/tests/test_daily_gap_confirmatory_run.py` => all checks passed.
- `git diff --check` => exit 0.
- JSON validation de decision, input/open/stat summaries y runtime summary/FDR => exit 0.
- `docker build -f backend/Dockerfile -t tradeo-backend:gap007 .` => exit 0.
- Security scan: no `artifacts/runtime`, `data/cache`, `.env`, `MEMORY.md`, `memory/`, signals, previews u orders nuevos versionados.

## I. Decision GAP-007
`GAP_CONFIRMATION_FAIL_OPEN_SLIPPAGE`.

## J. Confirmacion restricciones
No ordenes. No paper. No live. No preview. No senales. No IBKR. No descargas. No cron. No `.env` real modificado. No gh. No main push. No candidate approval. No DSS-005.

## K. Siguiente tarea recomendada
Cerrar gap same-day reversal como no robusto bajo realismo de open, o volver al roadmap para elegir una familia distinta. Si Direccion insiste en gap, redisenar solo con protocolo nuevo y sin reciclar esta observacion como candidato.
