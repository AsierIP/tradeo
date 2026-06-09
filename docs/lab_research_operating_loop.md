# Lab and Research Operating Loop

Fecha: 2026-06-09

## Objetivo

Tradeo separa descubrimiento, validacion paper y produccion. Research puede
encontrar familias visuales y proponer hipotesis, pero Lab debe acumular verdad
operativa antes de que Director permita cualquier promocion.

El flujo esperado es:

1. Research descubre o revisa patrones.
2. Lab escanea el mercado actual y genera variantes de entrada.
3. Cada oportunidad queda deduplicada y auditada.
4. Las oportunidades de Lab crean observaciones paper/shadow, sin enviar ordenes.
5. Las observaciones cerradas alimentan ranking, regimenes, variantes y Director.
6. Director decide que estudiar, congelar o mantener como research-only.
7. El audit bridge exporta un paquete reproducible para revisar el estado.

## Research

Research trabaja con labels path-dependent, embeddings enriquecidos, discovery
por regimen y validacion anti-overfit. Sus resultados se guardan como patrones
descubiertos y memoria de investigacion.

Research no puede promocionar directamente a ejecucion. Un patron con buen score
solo pasa a ser candidato para Lab si sobrevive a filtros estadisticos y al
Director gate.

## Lab Scanner

Lab convierte cada match de Research en oportunidades de entrada concretas.
Para cada oportunidad calcula:

- `entry_variant_id` y descripcion de la variante;
- precio de entrada, stop, target y reward/risk;
- `entry_gate` y `base_entry_gate`;
- `entry_audit` anti-lookahead;
- `regime` y `regime_fit`;
- componentes de ranking;
- razones exactas de rechazo.

Los matches se deduplican por:

```text
pattern_id + symbol + timeframe + entry_variant_id + window_end
```

Si llega el mismo match otra vez, Tradeo actualiza metadata y score en vez de
crear filas repetidas.

## Paper/Shadow Observations

Lab puede crear observaciones internas de tipo `lab_shadow_observation`.

Estas observaciones:

- no llaman a IBKR;
- no mandan ordenes;
- usan el precio/stop/target calculado por la variante;
- se cierran por target, stop o timeout cuando llegan nuevas barras;
- alimentan historial por patron, variante y regimen.

El objetivo es generar datos para decidir, no simular ejecucion live perfecta.

### Near-Miss Shadow

Lab tambien puede abrir observaciones shadow para near-misses de alta prioridad
aunque `entry_gate` falle por confirmacion de volumen moderada. Esto solo aplica
a `laboratory`; Fox Hunter y produccion no cambian.

La observacion near-miss exige:

- `entry_variant_id`;
- `regime.regime_key`;
- ranking alto o `opportunity_rank_score` suficiente;
- fallo blando por `insufficient_volume` o `weak_volume_confirmation`;
- sin blockers duros como trigger inexistente, regimen invalido, exceso de ATR,
  sobreextension, score de entrada debil o riesgo rechazado.

Estas senales/observaciones quedan marcadas con:

- `entry_variant_id`;
- `regime`;
- `entry_gate`;
- `entry_quality`;
- `opportunity_rank`;
- `opportunity_rank_score`;
- `near_miss=true`;
- `near_miss_shadow=true`;
- `would_have_failed_entry_gate=true`;
- `paper_only=true`;
- `no_ibkr_order=true`;
- razones exactas en `near_miss_reasons`.

Cuando cierran, cuentan como historial shadow de Lab para ranking y Director.
No relajan promociones: Director sigue bloqueando hasta que su gate apruebe
evidencia suficiente.

El objetivo es generar historia Lab cerrada para Director sin relajar ejecucion.
Director sigue bloqueando promociones hasta que haya evidencia paper suficiente.

## Ranking

El ranking combina:

- calidad de entrada;
- similitud contra el patron;
- edge de Research;
- reward/risk;
- liquidez;
- fit de regimen;
- historial paper cerrado cuando existe;
- bonus pequeno de exploracion para variantes con poca muestra.

Si no hay historial paper, el ranking cae a score Research + entry score. La
metadata debe explicar que componentes se usaron.

## Director

Director agrega Lab execution dentro de `metrics_json["lab_execution"]`.
Cuando hay trades cerrados, separa:

- rendimiento por `entry_variant_id`;
- rendimiento por `regime_key`;
- drawdown, expectancy, winrate y profit factor;
- diferencia contra baseline y contra Research.

Cuando no hay datos suficientes, Director debe decirlo de forma accionable:

- cuantos trades faltan;
- que buckets siguen vacios;
- que patron debe permanecer congelado;
- que evidencia falta para revisar promocion.

## Audit Bridge

El audit bridge genera paquetes reproducibles bajo:

```text
research/audit_bridge/requests/<AUDIT_ID>/
```

El contrato actual exige:

- manifest y conteos coherentes;
- configuracion redacted;
- `paper_trades.csv` y `ib_fills.csv` consistentes;
- sin fills huerfanos;
- duplicados reportados;
- Director gate presente;
- `metrics_by_regime.csv`;
- `metrics_by_entry_variant.csv`;
- buckets vacios con `empty_reason` cuando no hay closed Lab trades.

Un paquete puede validar tecnicamente y aun asi quedar `blocked`. Eso es normal:
blocked significa que no hay suficiente evidencia para promocionar, no que el
export este roto.

## Dashboard

El dashboard de Laboratorio muestra diagnostico de solo lectura desde:

```text
GET /api/laboratory/diagnostics?limit=24
```

Debe ayudar a responder:

- que oportunidades se estan viendo;
- que variante y regimen corresponden;
- por que entry gate rechazo;
- que historial paper existe;
- que falta para promover;
- que oportunidades son near-miss.

## Invariantes De Seguridad

- `live_armed=false` salvo decision humana explicita.
- Lab no envia ordenes live.
- Shadow observations no llaman a IBKR.
- Fox Hunter solo usa patrones de produccion.
- Director no promociona automaticamente.
- Los exports no deben contener secretos ni account IDs reales.

## Estado Esperado Tras Redeploy

Un estado sano durante mercado abierto puede ser:

- backend y worker healthy;
- IBKR health OK;
- Lab encuentra matches;
- entry gate rechaza oportunidades debiles;
- shadow observations empiezan a acumular evidencia;
- Director sigue bloqueando promociones hasta tener trades/fills suficientes;
- audit export valida contrato pero puede quedar `blocked` por falta de evidencia.

## Operacion 2026-06-09

Tras el redeploy del ciclo Lab/Research se detectaron duplicados historicos en
`discovered_pattern_matches`. Se dejaron 877 matches unicos vivos por la clave:

```text
pattern_id, symbol, timeframe, entry_variant_id, window_end
```

Las 53.381 filas duplicadas se conservaron en la tabla local de backup
`discovered_pattern_matches_dedupe_backup_20260609`. Despues de repetir un scan
manual limitado, la DB siguio con `duplicate_rows=0`, confirmando que el upsert
actual no vuelve a crear duplicados exactos.

El paquete
`TRADEO-AUDIT-20260609-1601_post_dedupe_health` queda como referencia post-fix:
el export es usable y genera los buckets nuevos, pero Director lo bloquea porque
aun no existen closed Lab trades ni fills IB Paper enlazados.
