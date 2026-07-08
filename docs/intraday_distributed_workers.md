# Intraday Distributed Research/Lab Workers v1

Objetivo: escalar Research-intradia y Laboratorio-intradia con workers sincronizados, sin duplicar graficos y sin meter GPT en el camino caliente de Lab.

## Decision tecnica

La primera version usa PostgreSQL como cola auditable. El patron recomendado es `SELECT ... FOR UPDATE SKIP LOCKED` en despliegues PostgreSQL, con fallback compatible en SQLite para tests. Redis Streams, Celery y Ray quedan como fases posteriores si el volumen supera lo que Postgres puede gestionar.

## Componentes

- `IntradayWorkDescriptor`: identidad canonica de una unidad de trabajo.
- `stable_work_fingerprint`: hash estable de grafico, timeframe, ventana, parametros, datos y split.
- `IntradayWorkItem`: tabla con dedupe duro, prioridad, lease, expiracion y resultado.
- `IntradayWorkerHeartbeat`: tabla de presencia/capacidad de workers.
- `IntradayDistributedWorkQueue`: enqueue, claim, complete, fail, expire, reap y metricas.

## Scopes

- `research`: trabajos de busqueda/validacion historica.
- `lab`: oportunidades paper/shadow en tiempo real.
- `committee`: cola posterior para patrones ya validados matematicamente.

## Garantias

- `UNIQUE(work_fingerprint)` evita analizar el mismo grafico/experimento dos veces.
- `lease_until` permite recuperar trabajo si un worker muere.
- `expires_at` evita que Lab procese oportunidades caducadas.
- `attempt_count/max_attempts` evita bucles infinitos.
- `payload_json/result_json/reason_codes_json` deja auditoria completa.

## Regla operativa

Research puede trabajar por lotes. Lab debe priorizar frescura: oportunidades intradia con `expires_at` vencido se marcan `expired` antes del claim.
