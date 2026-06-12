# P0 Matcher: kNN/Mahalanobis + umbral conformal + ambigüedad con dientes (2026-06-12)

Scope: fila P0 del `INFORME_MEJORA_TRADEO_V1_PRECISION` — §3.1.1 (kNN a medoids),
§3.1.2 (Mahalanobis diagonal), §3.1.3 (umbral conformal con garantía),
§3.1.4 (ambigüedad con dientes), más el prerequisito §2.3.4 (medoids +
covarianza persistidos por patrón).

## Qué cambia

### 1. `research/prototype_bank.py` (nuevo, módulo compartido)

Una sola implementación de las distancias y del τ conformal que importan tanto
Research como el matcher de Lab — la paridad Research↔Lab queda garantizada por
construcción, no por tests de espejo:

- `knn_distance`: media de las k=3 menores distancias L2 escaladas a los
  medoids, normalizada por √dim (misma escala que la distancia legacy al
  centroide).
- `mahalanobis_diag_distance`: distancia Mahalanobis diagonal media-normalizada
  con varianza regularizada (`σ² + ε`, ε = max(1e-9, 0.05·media(σ²))).
- `conformal_tau`: fórmula exacta del informe §10.2 — `k = ⌈(n+1)(1−α)⌉`,
  garantía de muestra finita `P(d ≤ τ) ≥ 1−α` bajo intercambiabilidad.
- `build_prototype_bank`: split 75/25 (proto/calibración) con RNG determinista;
  medoids (≤16, miembros reales vía MiniBatchKMeans + nearest member), centro y
  covarianza diagonal SOLO del subconjunto proto; τ_knn y τ_maha conformales
  sobre las distancias del subconjunto de calibración (disjunto ⇒ scores
  conformales válidos). Devuelve `None` con <8 miembros (el patrón conserva el
  gate legacy).
- `parse_prototype_bank`: validación fail-closed del bank persistido (shape,
  taus finitos y positivos, varianzas > 0); cualquier banco corrupto ⇒ gate
  legacy, nunca un gate a medias.

### 2. Research — `ClusterResearchEngine` (§2.3.4 + §3.1.3)

Tras `match_tau_similarity`, cada cluster persiste `metrics["prototype_bank"]`
construido con los **miembros de TRAIN únicamente** (`matrix_train_scaled[train_idxs]`;
el holdout temporal nunca entra en el banco). Seed determinista por cluster
(`random_state·1000003 + window_size·101 + cluster_id`) — compatible con el
contrato de determinismo bit a bit de discovery (verificado: `test_discovery_determinism`
pasa con el banco incluido en el payload canónico).

Nuevos campos del engine cableados desde Settings en `PatternDiscoveryLabAgent`:
`conformal_alpha` (0.10), `prototype_medoid_count` (16), `prototype_knn_k` (3).

### 3. Lab — `NovelPatternMatcher` (§3.1.1–3)

`_similarity_diagnostic` consulta `_conformal_gate`:

- Con banco válido y `discovery_match_conformal_gate_enabled` (default ON):
  `passed = (similaridad ≥ floor global) AND (d_knn ≤ τ_knn) AND (d_maha ≤ τ_maha)`.
  El τ-percentil 92.5 por patrón queda **sustituido** como criterio; el floor
  global (`discovery_match_similarity_threshold`) se mantiene como freno de
  operador y la similitud al centroide se sigue publicando como diagnóstico de
  continuidad (`centroid_similarity_role: diagnostic_only`), tal y como pide el
  informe.
- Sin banco (patrones antiguos), banco con dimensión incompatible o flag OFF:
  comportamiento legacy bit a bit (τ-percentil por patrón sobre el floor).
- El diagnóstico completo (`d_knn`, `d_maha`, taus, α, k, medoid_count, pass por
  eje) viaja en el match y en `metrics_json` del `DiscoveredPatternMatch`
  (`conformal_gate`) para auditoría y para el harness de §3.1.5.

### 4. Scanner — ambigüedad con dientes (§3.1.4)

`PatternEntryScanner._ambiguity_gate`, tras el check de calidad estándar:

- Si `ambiguity_ratio ≥ entry_ambiguity_ratio_threshold` (0.95), el match debe
  superar `entry_min_quality_score + entry_ambiguity_quality_margin` (+0.10,
  "un nivel más").
- Si no lo supera: abstención. Audit log `entry_match_rejected_by_ambiguity`,
  contador `rejected_by_ambiguity` en el resultado del scan, y en Laboratory se
  abre una observación shadow near-miss con motivo **`ambiguous_match`**
  (`near_miss_type=ambiguous_match_shadow`,
  `opened_reason=lab_near_miss_ambiguous_match_shadow_observation`) ⇒ el
  outcome queda observable y alimenta el dataset del meta-modelo (§3.2).
- La decisión (ratio, bar exigido, score, passed) se anota en el match aunque
  pase, para auditoría en señales almacenadas.
- La cláusula `p_meta ≥ p* + 0.05` del informe queda documentada en config para
  activarse cuando exista el meta-modelo (P1 §2.4); hoy no hay p_meta.

Flags nuevos (todos en `core/config.py`): `discovery_match_conformal_gate_enabled=True`,
`discovery_match_conformal_alpha=0.10`, `discovery_match_prototype_medoids=16`,
`discovery_match_knn_k=3`, `entry_ambiguity_gate_enabled=True`,
`entry_ambiguity_ratio_threshold=0.95`, `entry_ambiguity_quality_margin=0.10`.

## Verificación

- 15 tests nuevos: `test_matcher_conformal_gate.py` (11, incluido el
  `test_conformal_threshold_coverage` que pedía el informe §7.4, cobertura
  estadística ≥1−α; gate bloquea vectores "cerca en media, fuera de la nube";
  fallbacks legacy/flag/dimensión) y `test_ambiguity_gate.py` (4: abstención
  con shadow, bar escalado superado, no-ambiguo, flag off).
- Suite completa backend: **330 passed, 1 skipped** (baseline 315+1). `ruff` limpio.
- Determinismo de discovery intacto (banco incluido en el hash de contenido).

## Pendientes reales / notas de integración

- **Solape con la rama del harness** (`fable5high/p0-harness-20260611`, commit
  `e470d5c`, sin push): ambas tocan `_similarity_diagnostic` y el bloque de
  persistencia de métricas del engine. Conflicto textual esperado al merge,
  semánticamente compatible: el pesado temporal γ cambia el espacio de la
  distancia legacy; el gate conformal es un criterio adicional. Si se adopta γ,
  el banco deberá reconstruirse con las distancias pesadas (re-run de
  discovery), igual que su τ.
- El harness §3.1.5 (rama hermana) debería añadir la curva FPR@recall90 del
  gate conformal junto a la del τ-percentil en el próximo run real de
  discovery; con eso se decide si α=0.10 es el punto correcto.
- Los patrones ya persistidos no tienen banco ⇒ siguen con gate legacy hasta el
  próximo run de discovery/rediscovery que los refresque.
- Re-rank DTW (§3.1.6) y fusión `score_forma` quedan fuera de este scope (P1).
