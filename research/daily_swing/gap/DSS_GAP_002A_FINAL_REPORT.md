# DSS-GAP-002A Final Report

## A. Resumen ejecutivo

T-DAILY-GAP-002A queda completada. Se localizo una cache Daily OHLCV research local compatible, se restauro como runtime no versionado y se relanzo GAP-002 cache-only. El ledger real quedo creado localmente y los summaries saneados pequenos quedaron bajo `research/daily_swing/gap`.

Decision: GAP_EVENT_LEDGER_READY_FOR_RESEARCH_DESIGN.

## B. Path real usado

`/tmp/tradeo-main-004k-clean`

## C. Rama y commit/push

Rama: `feature/daily-gap-protocol-001`.

Commit/push: pendiente hasta el commit final validado.

## D. Cache discovery

Decision parcial: CACHE_CANDIDATE_FOUND.

Mejor candidato:

`/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001/artifacts/runtime/daily_swing/daily_ohlcv_research`

152 CSV, ~13M, SPY/QQQ presentes. Universo seleccionado: `dss_003e_research_universe_checked.csv`, 152 filas, 150 simbolos operativos, 2 benchmarks.

## E. Cache compatibility gate

Decision parcial: CACHE_COMPATIBLE.

Columnas OHLCV requeridas presentes. SPY/QQQ presentes como benchmarks ETF. Product classes: ETF/STK; clases operativas: STK only. Barra falsa `2026-07-03` ausente. Ultima fecha del ledger: 2026-07-02.

## F. Runtime restore

Decision parcial: RUNTIME_RESTORE_READY.

Restauracion por symlink local no versionado:

- `artifacts/runtime/daily_swing/daily_ohlcv_research`
- `artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv`
- `artifacts/runtime/daily_swing/gap`

`artifacts/runtime` no se versiona.

## G. Ledger rerun result

Decision parcial: GAP_LEDGER_RERUN_READY.

- Ledger local: `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv`
- Ledger versionado: no.
- Filas: 114304.
- Simbolos total: 152.
- Simbolos operativos: 150.
- Fechas: 2023-07-05 a 2026-07-02.
- Eventos ready: 54942.

## H. No-lookahead / field availability audit

NO_LOOKAHEAD_PASS.

`gap_pct` usa `open_t` y `prev_close`. `prior_return_5d`, `prior_return_20d` y `atr14_pct_prev` usan datos previos. `open_to_close_return`, `close_to_next_open_return`, `next_open_to_close_return`, `intraday_gap_fill_flag` y `gap_fill_ratio` quedan como outcome/analysis fields, no senal open.

## I. Coverage/distribution summary

Event quality:

- GAP_EVENT_READY: 54942.
- GAP_EVENT_TOO_SMALL: 54809.
- GAP_EVENT_INSUFFICIENT_HISTORY: 3000.
- GAP_EVENT_BENCHMARK_ONLY: 1504.
- GAP_EVENT_SPLIT_ADJUSTMENT_SUSPECT: 49.

Threshold inventory:

- abs_gap_pct >= 0.5%: 56864.
- abs_gap_pct >= 1.0%: 29771.
- abs_gap_pct >= 2.0%: 11220.
- abs_gap_pct >= 3.0%: 5529.
- abs_gap_pct >= 5.0%: 2050.
- abs(gap_vs_atr_prev) >= 0.5: 14072.
- abs(gap_vs_atr_prev) >= 1.0: 3321.
- abs(gap_vs_atr_prev) >= 1.5: 1630.

No se selecciono mejor umbral, no se infirio edge y no se eligio continuation/reversal.

## J. Tests/validaciones

Comandos ejecutados:

- `docker run ... python scripts/build_daily_gap_event_ledger.py --cache-only --no-ibkr` => exit 0.
- `python3 -m py_compile scripts/build_daily_gap_event_ledger.py backend/tradeo/modules/daily_swing/gap_event_ledger.py` => exit 0.
- `docker run ... pytest -q backend/tradeo/tests/test_daily_gap_protocol.py backend/tradeo/tests/test_daily_gap_event_ledger.py` => 18 passed, exit 0.
- `docker run ... ruff check backend/tradeo/modules/daily_swing/gap_event_ledger.py scripts/build_daily_gap_event_ledger.py backend/tradeo/tests/test_daily_gap_event_ledger.py` => exit 0.
- `git diff --check` => exit 0.
- Security scan: no tracked `artifacts/runtime`, no tracked `MEMORY.md`/`memory/`, no tracked real `.env`; only `.env.example` is tracked.
- `docker build -f backend/Dockerfile -t tradeo-backend-gap002a-test .` => exit 0.

## K. Decision GAP-002A

GAP_EVENT_LEDGER_READY_FOR_RESEARCH_DESIGN.

## L. Seguridad

Confirmado: no ordenes, no paper, no live, no preview, no senales, no backtest, no IBKR, no descargas, no cron, no `.env` real modificado, no gh, no push a main, no DSS-005.

## M. Siguiente tarea recomendada

T-DAILY-GAP-003 - Design cache-only gap research backtest matrix, no execution.

No ejecutarla en esta tarea.
