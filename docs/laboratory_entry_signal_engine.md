# Laboratory Entry Signal Engine

Fecha: 2026-06-09

## Objetivo

Laboratorio ya no trata un match de Research como una entrada unica. Ahora convierte cada match en candidatos de entrada auditables, aprende de paper trades cerrados y prioriza solo la mejor oportunidad por patron/simbolo en cada scan.

## Cambios

### 1. Scanner mas rapido

- `NovelPatternMatcher.match_current` agrupa patrones por `timeframe`.
- Descarga cada `(symbol, timeframe)` una sola vez por scan.
- Calcula cada embedding `(symbol, timeframe, window_size)` una sola vez.
- Compara ese embedding contra todos los centroides compatibles.
- SPY/QQQ se cachean por timeframe para contexto de fuerza relativa.

### 2. Variantes de entrada

Cada match puede generar variantes:

- `*_next_bar_limit`: entrada tras breakout/reclaim/momentum confirmado.
- `next_bar_stop_confirmation`: exige continuacion por encima/debajo del extremo de la vela.
- `next_bar_limit_retest`: espera retest cerca del nivel de ruptura/reclaim.
- `volume_confirmed_close`: variante con confirmacion de volumen.
- `gap_open_follow_through`: gap con continuacion hasta cierre.

Laboratorio considera varias variantes, pero procesa solo la mejor por `(symbol, pattern)` en cada scan para evitar exposicion duplicada.

### 3. Anti-lookahead operativo

Cada match/senal guarda:

- `available_data_cutoff_ts`
- `decision_ts`
- `entry_eligible_ts`
- `label_generated_ts`
- `source_bar_hash`
- `split_id`

La regla es simple: una entrada solo es elegible despues del cutoff de datos usados para decidir.

### 4. Regime router

Cada match conserva `regime_key` con:

- regimen de mercado;
- tendencia;
- volatilidad;
- liquidez;
- fuerza relativa vs SPY.

Si Research guardo `regime_profile`, el matcher calcula `regime_fit` para favorecer setups en regimenes ya vistos por el patron.

### 5. Ranking adaptativo

`opportunity_ranking` ahora usa:

- calidad de entrada;
- similitud;
- edge de Research;
- reward/risk;
- liquidez;
- fit de regimen;
- historial de ejecucion real por patron, simbolo, variante y regimen;
- bonus pequeno de exploracion cuando una variante tiene poca muestra.

El historial sale de trades cerrados de Laboratorio, no de metricas teoricas de Research.

### 6. Paper truth y Director

- Las senales guardan `entry_variant_id`, `entry_variant`, `entry_audit`, `regime` y `regime_fit`.
- `IBKRBroker.submit_signal_bracket` copia esos campos al trade.
- `DirectorReviewGate` agrega performance por variante y regimen dentro de `pattern.metrics_json["lab_execution"]`.
- El audit exporter ya puede exportar `paper_trades.csv` e `ib_fills.csv` desde el overview de Laboratorio cuando existan.

### 7. Diagnostico UI/API

- `GET /api/laboratory/diagnostics?limit=24` es un endpoint de solo lectura para presentacion.
- Combina senales paper candidatas, rechazos en `audit_logs` y `discovered_pattern_matches` recientes.
- Cada fila resume simbolo, patron, variante, regimen, rank/score, razon de rechazo, componentes de `entry_gate`, historial paper por patron/variante/regimen y blockers para promocion.
- No ejecuta scanner, no crea senales y no envia ordenes.
- El dashboard muestra esta informacion en `Laboratorio -> Diagnostico Lab`.

## Invariantes

- Laboratorio sigue siendo paper-first.
- Fox Hunter sigue usando solo patrones `production`.
- No hay promocion automatica a Produccion.
- Director sigue exigiendo trades/fills reales antes de aprobar.
- La UI solo muestra diagnosticos de presentacion; no cambia ejecucion.
