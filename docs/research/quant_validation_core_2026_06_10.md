# Núcleo de validación cuantitativa (Fase 1-2 del informe de mejora)

Fecha: 2026-06-10 · Rama: `feature/quant-validation-core`
Origen: `INFORME_MEJORA_TRADEO.md` (informe externo de revisión cuantitativa) +
módulo entregado `quant_validation.py`.

## Qué se implementó

### 1. `tradeo/research/quant_validation.py` (nuevo)

Módulo autocontenido (numpy + stdlib) con el pipeline de inferencia selectiva:
`select_nonoverlapping_events`, `average_uniqueness_weights` (n_eff, López de
Prado), `triple_barrier_outcome` (fills pesimistas: entrada en open(t+1), gaps
por stop al OPEN, gaps por target al TARGET, both-touch ⇒ stop, time stop,
MFE/MAE en R), `stationary_bootstrap_ci`, `newey_west_tstat`,
`permutation_pvalue`, `benjamini_hochberg`, `expected_max_sharpe` /
`probabilistic_sharpe_ratio` / `deflated_sharpe_ratio`, `purged_walk_forward`,
`pbo_cscv`, `cusum_drift`, `summarize_pattern_validation`.

Golden tests en `tradeo/tests/test_quant_validation.py` (los 6 casos del
contrato de simulación §6 del informe, propiedad de no-solapamiento, n_eff,
BH-FDR, monotonía del DSR, no-leakage del walk-forward purgado, CUSUM).

### 2. Pseudo-replicación / n_eff (P0-1)

`ClusterResearchEngine._quant_validation_metrics()`: por candidato, los spans
de outcome se colocan en un eje de días de calendario común, se deduplica por
símbolo (no puedes estar en dos trades solapados del mismo patrón) y los
supervivientes reciben pesos de unicidad media. Se persiste en
`metrics.quant_validation` (n_raw / n_unique / n_eff, expectancy y PF
ponderados, IC95 stationary bootstrap, t Newey-West, skew/kurtosis) y en
`metrics.effective_sample_count`.

Gate duro en `ValidationGate`: `n_eff >= TRADEO_DISCOVERY_MIN_EFFECTIVE_SAMPLES`
(60 por defecto). El conteo bruto (`discovery_min_samples`) se mantiene.

### 3. Multiplicidad a nivel de run (P0-2)

`PatternDiscoveryLabAgent._apply_run_level_inference()`:

- **BH-FDR** (`q = TRADEO_DISCOVERY_FDR_Q = 0.05`) sobre los `null_p_value`
  (permutación estratificada ya existente) de TODOS los clusters del run,
  aceptados y rechazados. `fdr_passed=false` ⇒ rechazo duro en el gate.
- **DSR de familia**: `deflated_sharpe_ratio` con `n = n_eff`,
  `N_trials = global_trial_count` previo del `GlobalExperimentRegistry` + los
  trials de este run (max `real_variant_count` por window-size), y `sr_std`
  estimada entre los Sharpe de los candidatos del run. `lab_candidate` exige
  `dsr_family >= TRADEO_DISCOVERY_MIN_DSR (0.95)` **y** IC95 inferior > 0 del
  expectancy ponderado; si falla, se degrada a `lab_watchlist` (no se rechaza:
  evidencia débil ≠ evidencia en contra).

Esto complementa (no sustituye) el `adjusted_p_value` Bonferroni-like, los
proxies WRC/SPA y el DSR per-cluster que ya existían.

### 4. Scheduler post-cierre (P0-8)

`TRADEO_DISCOVERY_SCAN_MINUTES` por defecto 90 → **1440**. En el worker,
`>= 1440` cambia el trigger a cron post-cierre
(`TRADEO_DISCOVERY_POST_CLOSE_HOUR_UTC=22:15`, lun-vie). Valores < 1440
conservan el comportamiento de intervalo (escape hatch).

### 5. Vela viva en el matcher (P0-3)

`NovelPatternMatcher._drop_incomplete_daily_bar()`: con
`TRADEO_DISCOVERY_MATCH_COMPLETE_BARS_ONLY=true` (default), antes de las 16:00
NY se descarta la barra diaria de hoy. La ventana operativa en sesión termina
en la barra de ayer — misma definición de barra que usó Research.

### 6. Umbral por patrón (P0-4)

Research persiste `match_tau_similarity` (percentil
`TRADEO_DISCOVERY_MATCH_TAU_PERCENTILE=92.5` de la distancia intra-cluster al
centroide, mapeada con la MISMA fórmula de similitud del matcher). El matcher
usa `max(suelo_global, tau_patron)`; `TRADEO_DISCOVERY_MATCH_SIMILARITY_THRESHOLD`
pasa a ser solo suelo. Cada match registra `similarity_threshold_used`.

### 7. Idempotencia de señal (P0-3/§4.1)

`PatternEntryScanner._signal_idempotency_key` =
`module|pattern_id|symbol|timeframe|entry_variant_id|window_end(bar_ts)`.
Se persiste en `Signal.metadata_json.signal_idempotency_key` y se comprueba
antes de crear señal (camino normal y near-miss shadow). Un re-scan de la misma
barra o un reinicio del worker no duplica señales (AuditLog
`entry_match_skipped_idempotent`).

## Decisiones y desviaciones respecto al informe

- El repo ya tenía mucho de la Fase 1 (null baselines estratificados, purged
  CV combinatorio, cost stress como gate, WRC/SPA proxies, DSR per-cluster).
  Se integró el módulo **encima** de eso, sin sustituir métricas existentes:
  los números nuevos viven en `quant_validation.*`, `fdr_*` y `dsr_family*`.
- El etiquetador de outcomes de discovery (`WindowSampler._path_outcome`,
  entrada al cierre de la ventana) NO se reemplazó en este cambio: cambiar la
  definición de entrada invalida la comparabilidad con todos los ledgers y
  patrones existentes. `triple_barrier_outcome` queda como contrato canónico
  (§6) listo para ShadowTracker/backtester y para una migración controlada del
  etiquetador (pendiente, ver abajo).
- RR levels: se mantiene la rejilla actual porque cada nivel ya se carga como
  trial en `real_variant_count` → el DSR de familia la penaliza. Reducir a
  2 niveles a priori (`2.5,4.0`) es un cambio de un parámetro en `.env` cuando
  Asier lo decida.
- El ratio de ambigüedad del matcher (margen vs 2º mejor patrón) no se
  implementó: las distancias entre patrones con scalers distintos no son
  directamente comparables; requiere diseño propio.

## Pendientes (orden sugerido)

1. Migrar el etiquetador de Research a `triple_barrier_outcome` (entrada en
   open(t+1)) con re-run completo y comparación antes/después.
2. ShadowTracker + implementation shortfall (§4.6) reutilizando
   `triple_barrier_outcome` como única implementación.
3. Reconciliación DB↔IBKR con kill switch automático (§4.5).
4. DirectorReviewGate secuencial (posterior bayesiano + SPRT + KS) (§4.7).
5. PatternHealthMonitor con `cusum_drift` sobre R por trade en producción
   (§4.8) — la función ya está disponible y testeada.
6. Universo point-in-time / snapshots mensuales (P0-5) y
   `survivorship_biased=true` en el ledger mientras tanto.
7. PBO/CSCV (`pbo_cscv`) en el ciclo del ImprovementAgent (§5).

## Aceptación

- `pytest`: 161 tests (39 nuevos) en verde; `ruff` limpio.
- Tras desplegar: el nº de `lab_candidate` por run debe **caer** (si no cae,
  revisar que `_apply_run_level_inference` corre antes del gate). Cada
  candidato lleva `fdr_*`, `dsr_family*` y `quant_validation` en su digest.
