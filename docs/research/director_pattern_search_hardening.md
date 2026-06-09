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
