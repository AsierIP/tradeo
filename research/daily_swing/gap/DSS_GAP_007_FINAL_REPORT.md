# DSS-GAP-007 Final Report

## A. Resumen ejecutivo
GAP-007 ejecutado cache-only contra la matriz cerrada GAP-006. Decision: `GAP_CONFIRMATION_FAIL_OPEN_SLIPPAGE`.

## B. Path real usado
`/tmp/tradeo-main-004k-clean`.

## C. Rama
`feature/daily-gap-protocol-001`.

## D. Input integrity
`CONFIRMATORY_INPUT_PASS`; 12 filas, 6 targets, ledger 114304 filas.

## E. Confirmatory execution summary
- GAP006_OBS1_REFERENCE_ALL: events OOS 3495, symbols 148, x2=0.3561%, PF x2=1.23743, 50bps=0.0561%.
- GAP006_OBS1_ONE_ACTIVE: events OOS 3495, symbols 148, x2=0.3561%, PF x2=1.23743, 50bps=0.0561%.
- GAP006_OBS1_MAX2: events OOS 686, symbols 107, x2=-0.2099%, PF x2=0.878991, 50bps=-0.5099%.
- GAP006_OBS2_REFERENCE_ALL: events OOS 7362, symbols 150, x2=0.1725%, PF x2=1.145552, 50bps=-0.1275%.
- GAP006_OBS2_ONE_ACTIVE: events OOS 7362, symbols 150, x2=0.1725%, PF x2=1.145552, 50bps=-0.1275%.
- GAP006_OBS2_MAX2: events OOS 250, symbols 21, x2=-0.2116%, PF x2=0.846896, 50bps=-0.5116%.

## F. Open realism / operability / earnings review
`OPEN_REALISM_FAIL`. Slippage adverso de open a 50/75 bps se mantiene como gate terminal si vuelve negativo. Earnings queda `earnings_unknown=true` y solo descriptivo.

## G. Statistical / baseline / placebo verdict
`STAT_BASELINE_PASS`. FDR/WRC/SPA-light `FDR_WRC_SPA_LIGHT_PASS` con min q=0.0.

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

## J. Seguridad
No ordenes, no paper, no live, no preview, no senales, no IBKR, no descargas, no cron, no gh, no main push.

## K. Siguiente tarea recomendada
Volver a roadmap o revisar diseno next-day solo si Direccion lo autoriza; no ejecutar aqui.
