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

## 4. Familias, Variantes Y Drift

Estado: implementado.

Cambios:

- `NovelPatternRegistry` mantiene:
  - `pattern_family_key`
  - `canonical_pattern_key`
  - `variant_key`
  - `variant_count`
  - `drift_status`
  - `drift_score`
- Patrones con centroides similares se fusionan en una familia canonica.
- Cada nuevo candidato similar queda registrado como variante del canonico.
- Si la nueva evidencia baja materialmente la expectancy frente al canonico, se marca `degrading`.
- Si mejora materialmente, se marca `improving`; si no, `stable`.

Lectura para Director:

- Una familia acumula evidencia de multiples runs sin inflar el numero de patrones.
- `variant_count` alto con `stable/improving` aumenta confianza.
- `degrading` indica que nuevos datos erosionan el edge y debe bloquear escalado.

Checklist de auditoria:

- No contar variantes similares como patrones independientes.
- Revisar familias con `drift_status=degrading`.
- Confirmar que el patron canonico conserva lineage de variantes.

## 5. Multi-Timeframe Y Relative Strength

Estado: implementado.

Cambios:

- El embedding incorpora contexto weekly calculado desde la ventana:
  - `weekly_return`
  - `weekly_trend`
- Discovery intenta descargar SPY y QQQ una vez por run.
- El embedding incorpora relative strength:
  - `relative_strength_spy`
  - `relative_strength_qqq`
  - `benchmark_alignment`
- El matcher actual tambien calcula SPY/QQQ para poder comparar patrones nuevos.
- Patrones antiguos siguen funcionando por compatibilidad de prefijo en el matcher.

Lectura para Director:

- Un patron con edge solo cuando la fuerza relativa es positiva puede requerir filtro operativo.
- `benchmark_alignment=-1` indica setup contrarian vs mercado; revisar por separado.
- Relative strength ayuda a separar setup local de simple beta de mercado.

Checklist de auditoria:

- Confirmar si el edge depende de SPY/QQQ.
- Separar patrones momentum de patrones contrarian.
- Revisar familias con mismo setup pero distinto contexto benchmark.

## 6. Stress Gates De Costes Y Slippage

Estado: implementado.

Cambios:

- `RewardRiskAnalyzer` soporta `cost_multiplier`.
- Research calcula `cost_stress` para multiplicadores configurados, por defecto:
  - `1x`
  - `2x`
  - `3x`
- `cost_stress_passed` exige expectancy positiva y PF >= 1 en el multiplicador requerido.
- `ValidationGate` rechaza si el edge no sobrevive `discovery_required_cost_stress_multiplier`, por defecto x2.

Lectura para Director:

- Si el patron falla con coste x2, el edge es demasiado fragil para promocion.
- `cost_stress` permite ver si el patron soporta spreads/slippage peores en small/mid caps.
- El coste base sigue viniendo de proxy de rango/liquidez por ventana.

Checklist de auditoria:

- Revisar `avg_execution_cost_r`.
- Exigir `cost_stress_passed=true` antes de Lab candidate serio.
- Comparar expectancy neta 1x vs 2x vs 3x.

## 7. Event Ledger Auditable

Estado: implementado.

Cambios:

- El agente genera el ledger completo por candidato en los runs de discovery.
- Cada ledger se persiste como artefacto comprimido `.json.gz` en:
  - `reports/research/event_ledgers/run_<run_id>/`
- El digest del patron conserva:
  - `event_ledger_path`
  - `event_ledger_sha256`
  - `event_ledger_count`
  - `event_ledger_compressed_bytes`
  - `event_ledger_uncompressed_bytes`
- El ledger raw se retira de `metrics_json` tras persistirlo para no inflar DB/reportes.
- Queda una preview compacta de los primeros eventos en `event_ledger_preview`.

Lectura para Director:

- El hash SHA-256 valida el contenido canonico sin comprimir.
- Si el patron se reevalua, se puede comparar ledger previo vs ledger nuevo por path/hash/count.
- El reporte de discovery ya muestra ruta y hash junto al patron.

Checklist de auditoria:

- Abrir el `.json.gz` del patron revisado.
- Verificar que `event_count` coincide con `event_ledger_count`.
- Validar que el hash del JSON descomprimido coincide con `event_ledger_sha256`.
- Revisar dispersion por simbolo, fecha, split y resultado R antes de aprobar promocion.
