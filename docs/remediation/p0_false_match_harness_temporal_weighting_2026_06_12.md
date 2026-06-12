# P0 — Harness de falsos matches (§3.1.5) + pesado temporal γ (§2.2.a)

Fecha: 2026-06-12 · Rama: `fable5high/p0-harness-20260611` · Informe: `INFORME_MEJORA_TRADEO_V1_PRECISION`

## Qué se implementó

### 1. Harness de falsos matches (§3.1.5)

`backend/tradeo/research/false_match_harness.py` — `FalseMatchHarness`.

Por cada patrón descubierto se construye un banco de negativos **disjunto por fuente**:

| Fuente | Construcción | Cubre |
|---|---|---|
| `same_symbol_outside_cluster` | Ventanas de los símbolos del cluster cuya etiqueta k-means ≠ cluster | Negativos duros (mismo subyacente) |
| `other_cluster_members` | Miembros de otros clusters del mismo `window_size`, símbolos distintos | Confusión entre patrones |
| `shadow_occurrences` | Opcional; vacío en research (las near-misses viven en el lab) | Hueco documentado, API lista |

Métrica publicada por patrón en `metrics_json`:

- `false_match_harness.fpr_at_recall` — **FPR@recall90**: tasa de falsos positivos al umbral de similitud que aún acepta el 90 % de los miembros reales del cluster. Desglose por fuente (`sources.*.fpr_at_recall`, `fpr_at_tau`, `max_similarity`).
- `false_match_harness.recall_at_tau` — recall de los positivos al `match_tau_similarity` persistido (la otra cara de la pareja del informe: recall garantizado / FPR estimado).
- `fpr_at_recall90` — alias top-level para el informe del run y vigilancia de drift.

La fórmula distancia→similitud es **idéntica bit a bit** a la de `NovelPatternMatcher` (test `test_harness_similarity_matches_matcher_formula`), de modo que los números del harness son directamente comparables con las similitudes en vivo. `_match_tau_similarity` del engine ahora reutiliza esa misma función (una sola fuente de verdad).

Submuestreo determinista de bancos grandes (cap 500/fuente, `random_state` del engine).

### 2. Pesado temporal del prefijo (§2.2.a)

`PatternEmbeddingEngine.temporal_weights(length, gamma=0.97)`: rampa `γ^(barras_desde_el_final)` sobre cada bloque downsampleado de 24 puntos (9 canales legacy + 3 enhanced); los features escalares mantienen peso 1.0. Se trunca al prefijo del centroide almacenado (compatibilidad con patrones antiguos).

- **Evaluación antes de adopción (gate del informe):** cada run de research publica el harness dos veces por patrón: `false_match_harness` (sin pesos) y `false_match_harness_temporal` (γ=0.97, con su propio τ: `match_tau_similarity_temporal`). La curva pesada se adopta solo si mejora `fpr_at_recall` en validación purgada — metadato `temporal_weighting.adoption_gate`.
- **Matcher (off por defecto):** `discovery_match_temporal_weighting_enabled=False`, `discovery_match_temporal_gamma=0.97` en `core/config.py`. Con el flag activo, el matcher aplica los pesos **solo** si el patrón persiste `match_tau_similarity_temporal` + `temporal_weighting.gamma` (paridad research↔lab: nunca compara similitud pesada contra τ sin pesar). Diagnóstico por match: `temporal_weighting.{enabled,gamma}`.
- **Bump de contrato:** `PatternEmbeddingEngine.contract(temporal_gamma=γ)` → `matcher_scaling = "train_fit_standard_scaler_prefix+temporal_gamma_0.97"`. El `feature_parity_contract` del matcher refleja el bump cuando el flag está activo.

## Archivos tocados

- `backend/tradeo/research/false_match_harness.py` (nuevo)
- `backend/tradeo/research/cluster_research_engine.py` — `_false_match_metrics`, integración en métricas, `match_temporal_gamma`
- `backend/tradeo/research/pattern_embedding_engine.py` — `temporal_weights`, contract con `temporal_gamma`, constantes de layout
- `backend/tradeo/research/novel_pattern_matcher.py` — vía pesada en `_similarity_diagnostic`, `_temporal_weighting_for_pattern`, `tau_key` en `_effective_threshold`
- `backend/tradeo/core/config.py` — 2 flags nuevos
- `backend/tradeo/tests/test_false_match_harness.py` (nuevo, 8 tests, incluye `test_false_match_harness_regression`)

## Verificación

- `pytest tradeo/tests/test_false_match_harness.py` → 8 passed
- Suite completa `pytest tradeo/tests/` → **323 passed, 1 skipped** (sin regresiones)

## Pendiente / fuera de alcance

- Banco `shadow_occurrences` real: requiere puente lab→research (las near-misses están en la DB del lab). API del harness ya lo acepta.
- Job nocturno de CI que ejecute el harness sobre datos sintéticos (§ recomendación 5 del informe).
- Vigilancia por DriftSentinel: no existe aún como servicio; `fpr_at_recall90` queda publicado en métricas para cuando se construya.
- Decisión de adopción del pesado temporal: comparar las dos curvas en el próximo run real de discovery y, si mejora, activar el flag.
