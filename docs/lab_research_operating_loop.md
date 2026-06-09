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
