AQUI CLAW - Tarea T-RESEARCH-CAPACITY-001 - Fase final - Estado OK

# CAPACITY-001 Final Report

## A. Resumen ejecutivo
Decision solicitada: Direccion puede evaluar si autoriza `T-RESEARCH-CAPACITY-002`.

Resultado: CAPACITY-001 queda en `RESEARCH_CAPACITY_BASELINE_READY`. Se definio el esquema de metricas, se inventario la superficie research, se ejecuto microbench seguro cache-only y se creo cola priorizada. No se aprobaron candidatos.

Riesgo principal: cache/search-space sigue siendo el cuello de botella; no hay paper_candidate ni shadow_candidate.

## B. Path real usado
`/home/vboxuser/tradeo-worktrees/research-capacity-001`

## C. Rama/commit/push
Base main SHA: `f47b76927d37034a239680312e212142d3f4cdd1`.

Rama: `feature/research-capacity-001`.

Head commit SHA: este reporte forma parte del commit de cierre; SHA final se comunica en el handoff al Director.

Compare URL: `https://github.com/AsierIP/tradeo/compare/main...feature/research-capacity-001`.

Archivos tocados:
- `backend/tradeo/modules/research_capacity/capacity_metrics.py`
- `backend/tradeo/tests/test_research_capacity.py`
- `scripts/run_research_capacity_microbench.py`
- `scripts/run_research_capacity_plan.py`
- `research/capacity/CAPACITY_001_*`
- `research/capacity/capacity_001_*`

Archivos NO tocados por seguridad: `.env`, `MEMORY.md`, `memory/`, `artifacts/runtime/`, broker/execution submit paths.

## D. Research surface inventory
- Daily modules: 18
- Intraday modules: 18
- Research docs: 79
- GAP reports: 44
- Cache files: 1477
- Cache timeframes: `{"15m": 48, "1d": 163, "1h": 117, "30m": 1100, "5m": 49}`
- Classified surfaces: 28
- Inventory artifacts: `CAPACITY_001_RESEARCH_SURFACE_INVENTORY.md`, `capacity_001_research_surface_inventory.csv`, `capacity_001_research_surface_inventory.json`

## E. Capacity metrics schema
`CAPACITY_001_METRICS_SCHEMA.md` define 35 campos obligatorios.

## F. Microbench results or blocker
Decision microbench: `RESEARCH_CAPACITY_BASELINE_READY`. Cache sampled 250 de 1477; rows_seen=200049; elapsed_seconds=0.306871.

## G. Experiment queue prioritized
6 experimentos priorizados; el primero es `RC-002-A`.

Allowed only after Director authorizes CAPACITY-002: `RC-002-A`.

Require separate Director approval: `RC-002-B, RC-002-C, RC-002-D, RC-002-E, RC-002-F`.

## H. Lab bottlenecks identified
Blockers principales: cache coverage, leakage controls, sample size/effective sample, FDR/WRC/SPA-light, cost_x2, OOS, drawdown y placebo gates.

## I. Throughput metrics baseline
Ver `capacity_001_microbench_summary.csv` y runtime JSON/CSV no versionados.

- windows_processed/cache rows: 200049.
- clusters_processed/cache files sampled: 250.
- candidates_accepted: 0.
- candidates_rejected parsed from prior artifacts: 221.
- near_misses parsed from prior artifacts: 5.
- top blockers parsed: cache=81, oos=27, placebo=26, spa=23, wrc=19, fdr=16, drawdown=14, cost_x2=5.

## J. Safety confirmation
live_allowed=false; paper_allowed=false; orders_allowed=false; order_code_changed=false; gates_relaxed=false; ibkr_readonly=not_checked; paper_trades=0; ib_fills=not_checked; kill_switch=not_checked; execution_automation_flags_all_false=true; no signals; no preview; no IBKR; no downloads; no gh; no main push.

## K. Tests/validaciones
| Comando | Exit code | Resultado | Tests |
| --- | ---: | --- | --- |
| `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile scripts/run_research_capacity_microbench.py scripts/collect_research_capacity_metrics.py scripts/run_research_capacity_plan.py backend/tradeo/modules/research_capacity/capacity_metrics.py` | 0 | OK | compile focal |
| `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... CAPACITY_001_OUTPUTS_OK` | 0 | OK | JSON/CSV/safety flags/candidates_accepted=0 |
| `python3 scripts/run_research_capacity_microbench.py --ibkr` | 2 | OK, unsafe positive flag blocked | safety guard |
| `python3 scripts/run_research_capacity_microbench.py --cache-only --dry-run --no-ibkr --no-orders --no-signals --no-preview --no-candidate-approval` | 3 | OK, missing `--no-downloads` blocked | safety guard |
| `git diff --check` | 0 | OK | whitespace |
| `docker build -f backend/Dockerfile . --progress=plain` | 0 | OK | backend image builds |
| `docker run --rm -v "$PWD/scripts:/scripts:ro" -w /app <image> pytest tradeo/tests/test_research_capacity.py tradeo/tests/test_daily_gap_matrix_dry_run.py tradeo/tests/test_intraday_research_wave_runner.py tradeo/tests/test_intraday_research_readiness.py -q` | 0 | OK | 47 passed |
| `docker run --rm -w /app <image> ruff check tradeo/modules/research_capacity/capacity_metrics.py tradeo/tests/test_research_capacity.py scripts/run_research_capacity_microbench.py scripts/collect_research_capacity_metrics.py scripts/run_research_capacity_plan.py` | 0 | OK | lint focal |
| `security scan touched files with rg + path denylist` | 0 | OK | no `.env`, memory, runtime, secrets, account ids, live/paper/order activation in touched files |

## L. Decision CAPACITY-001
`RESEARCH_CAPACITY_BASELINE_READY`

## M. Siguiente decision esperada
Si Direccion acepta, ejecutar `T-RESEARCH-CAPACITY-002` con primeros experimentos cache-only priorizados. Ningun experimento podra aprobar candidatos ni producir senales/paper sin tarea separada.

## N. Artifacts
- `research/capacity/CAPACITY_001_DECISION.json` - 847 bytes - sha256 `095400575faa2ddd8a9e4d9697b9e2283e6a24c8ac5ee3eb09afa1b87e333c2a`
- `research/capacity/capacity_001_experiment_queue.json` - 5707 bytes - sha256 `e6fa45b8b0d50cd39e598c378dd73df18852d7a5d6b8e57ccb4cbbe547f0996a`
- `research/capacity/capacity_001_research_surface_inventory.json` - 14899 bytes - sha256 `35c2ce2dbf3ed2a00f9753ac867448407663cf27fab0fa2fb9fa8f5e3ea6a437`
- `research/capacity/capacity_001_microbench_summary.csv` - 2087 bytes - sha256 `7c85e269ab7b69ba796de1c415a13bb8bf08f49b0c00b9359d6eaea8994980f8`

## O. Bloqueos y decision requerida
Bloqueos: no hay candidato; CAPACITY-001 no ejecuta research productivo ni aprueba candidatos.

Decision requerida: autorizar o no `T-RESEARCH-CAPACITY-002`. Si se autoriza, solo `RC-002-A` queda permitido dentro de esa tarea; `RC-002-B..F` requieren aprobacion separada.
