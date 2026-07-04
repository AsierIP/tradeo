# DSS-003E-4 Final Report

Generated at: 2026-07-04T15:03:50Z

## A. Resumen ejecutivo

DSS-003E-4 completada. La sesion IB Gateway Paper 4002 siguio sana: TCP host/Docker OK, canary inicial SPY/AAON 5D OK, y canary SPY/AAON 5D OK antes de cada batch. Se completo la cache research-150 en batches pequenos con resume/quarantine/caps. El quality gate research paso con operational_ready=150, benchmark_ready=2, sin barra fake 2026-07-03 y last_valid_bar_date=2026-07-02. No se ejecuto DSS-004E, backtest, senales, preview ni ordenes.

## B. Path real usado

/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001

## C. Rama, commit y push

Rama: feature/daily-swing-paper-probe-001.

Commit base: a48eb2d docs(daily): record DSS-003E-4 cache pass. Push final: ver commit posterior de correccion de decision si aplica.

## D. Preflight IBKR 4002 y canary inicial

- 127.0.0.1:4002: TCP_OK.
- host.docker.internal:4002 desde Docker: TCP_OK.
- Clasificacion: IB_GATEWAY_PAPER.
- read_only=true.
- 4001/7496: bloqueados por guard LIVE_PORT_RISK, no usados.
- SPY 5D: OK, bars_count=5.
- AAON 5D: OK, bars_count=5.

## E. Batch plan

- Universo: artifacts/runtime/daily_swing/dss_003_universe_research.csv.
- Universo operativo: 150 acciones.
- Benchmarks: SPY y QQQ benchmark_only.
- Cache previa reutilizada: 10 CSV del mini batch DSS-003E-R.
- Batch size objetivo: 25 nuevos fetches.
- Controles: resume, max_new_fetches=25, max_consecutive_timeouts=2, request_timeout=25, retry_count=1, retry_backoff_seconds=2, quarantine_failures=true, continue_on_symbol_timeout=true, stop_on_global_timeout=true.

## F. Cache research

- Estado final: CACHE_WRITTEN.
- CSV finales en daily_ohlcv_research: 152.
- Nuevos CSV escritos durante DSS-003E-4: 142.
- Cache previa reutilizada: 10.
- failed=0.
- quarantined=0.
- Verificacion final del runner: fetched=0, skipped=152, failed=0.

## G. Canary por batch

SPY 5D y AAON 5D pasaron antes de los 6 batches ejecutados.

Artifact: artifacts/runtime/daily_swing/dss_003e_4_batch_canaries.csv.

## H. Simbolos fallidos/quarantined

No hubo simbolos fallidos ni quarantined.

## I. Quality gate research

data_gate=PASS.

## J. operational_ready y benchmark_ready

- operational_ready=150.
- benchmark_ready=2.

## K. 2026-07-03 sin barra fake

false_bar_2026_07_03_present=false.

## L. last_valid_bar_date

last_valid_bar_date=2026-07-02.

## M. Seguridad

Confirmado: no ordenes, no paper orders, no live orders, no paper execution, no backtest, no senales, no preview operativo, no cron, no .env real modificado, no merge, no PR nuevo, no gh.

## N. Decision DSS-003E-4

DATA_GATE_RESEARCH_PASS.

## O. Siguiente fase recomendada

Esperar autorizacion explicita de Direccion antes de ejecutar DSS-004E. La siguiente fase tecnica razonable es backtest/revalidacion research sobre cache research-150, sin generar senales ni preview operativo salvo nueva orden.
