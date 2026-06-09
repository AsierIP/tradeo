# Director Research Pattern Search Hardening

Fecha: 2026-06-09

## Objetivo

Endurecer la busqueda de patrones de Research para que el Director reciba evidencia auditable, reproducible y resistente a overfitting antes de permitir cualquier avance hacia Lab/produccion.

## 1. Walk-Forward Rolling Con Embargo

Estado: implementado.

Cambios:

- Cada patron descubierto conserva el fit train-only ya existente para scaler/KMeans/R:R.
- Ademas calcula folds walk-forward cronologicos dentro del cluster.
- Cada fold elige `best_rr` solo con train del fold.
- La validacion del fold empieza despues de `discovery_walk_forward_embargo_samples`.
- Se publican `walk_forward_folds`, `walk_forward_positive_fold_rate`, `walk_forward_avg_expectancy_r`, `walk_forward_min_expectancy_r` y `walk_forward_pooled`.
- `ValidationGate` rechaza candidatos con folds suficientes si `walk_forward_positive_fold_rate < discovery_min_walk_forward_positive_rate`.

Lectura para Director:

- `walk_forward_positive_fold_rate` bajo indica edge concentrado en pocos periodos.
- `walk_forward_min_expectancy_r` negativo indica al menos un regimen donde el patron falla.
- Candidatos sin folds suficientes no se promocionan por esta evidencia; quedan con warning.

Checklist de auditoria:

- Confirmar que `validation_method` es `train_fit_forward_holdout_walk_forward_embargo`.
- Revisar que fold train/validation no se solapan.
- Revisar `embargo_samples`.
- Comparar OOS agregado contra folds individuales.

## 2. Null/Baseline Estratificado, Bootstrap Y Overfit

Estado: implementado.

Cambios:

- El null baseline ya no compara contra una poblacion cruda.
- Cada draw preserva estratos de `year`, regimen de volatilidad y regimen de tendencia.
- Se publican `null_method`, `null_strata_count`, `null_expectancy_r`, `expectancy_lift_r`, `null_p_value` y `adjusted_p_value`.
- Se calcula bootstrap determinista sobre resultados train del patron:
  - `expectancy_ci_low`
  - `expectancy_ci_high`
  - `profit_factor_ci_low`
- Se calcula `overfit_score` usando gap entre train y walk-forward junto con tasa de folds positivos.
- `ValidationGate` rechaza si:
  - `expectancy_ci_low < discovery_min_expectancy_ci_low`
  - `overfit_score > discovery_max_overfit_score`

Lectura para Director:

- `expectancy_lift_r` mide cuanto gana el patron frente a una entrada aleatoria comparable por regimen.
- `expectancy_ci_low <= 0` indica que el edge no es robusto en bootstrap.
- `overfit_score` cerca de 1 indica fuerte degradacion fuera de train o folds inconsistentes.

Checklist de auditoria:

- Revisar que `null_method` sea `stratified_regime_bootstrap`.
- Confirmar que `adjusted_p_value` incluye penalizacion por numero de variantes evaluadas.
- Exigir CI positivo antes de cualquier escalado serio.
- Tratar `overfit_score` alto como veto salvo explicacion de regimen.

## 3. Lifecycle Real De Confirmacion

Estado: implementado.

Cambios:

- Se anaden estados de patron:
  - `needs_confirmation`
  - `confirmed_candidate`
  - `failed_confirmation`
- `discovered_patterns` guarda columnas dedicadas:
  - `confirmation_status`
  - `confirmation_priority_score`
  - `confirmation_reason`
  - `confirmation_next_action`
  - `confirmation_attempts`
- Los candidatos fuertes pero underpowered ya no son solo `rejected` con metadata JSON.
- Si `ValidationGate` recomienda confirmacion, `NovelPatternRegistry` persiste el patron como `needs_confirmation`.
- `/api/research/confirmation-queue` filtra por columna DB y ordena por prioridad.

Lectura para Director:

- `needs_confirmation` no es aprobacion ni promocion.
- Es una cola formal para re-run ampliado con mismo setup/side/window antes de volver a evaluar.
- `confirmation_priority_score` ayuda a ordenar coste computacional vs promesa estadistica.

Checklist de auditoria:

- Revisar que ningun `needs_confirmation` pueda alimentar Fox/produccion.
- Exigir nuevo run ampliado antes de cambiar a `confirmed_candidate`.
- Si el re-run falla, marcar `failed_confirmation` y conservar evidencia.
