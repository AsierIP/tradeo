# Research Audit Bridge

`research/audit_bridge/` es el nexo comun entre Claw y ChatGPT para auditar el laboratorio de research de trading de Tradeo.

La carpeta define un contrato estable: Claw exporta paquetes reproducibles con patrones, eventos, trades, fills, configuracion y linaje de datos; ChatGPT los revisa con el mismo formato cada vez y puede comparar calidad estadistica, sesgos, bugs del laboratorio, data leakage, lookahead bias, costes, ejecucion y robustez.

## Crear un nuevo paquete

Cada auditoria vive en:

```text
research/audit_bridge/requests/<audit_id>/
```

El `audit_id` debe ser estable y legible, por ejemplo:

```text
2026-06-07_ib_paper_patterns
```

Flujo recomendado:

1. Crear una rama dedicada, nunca trabajar directo sobre `main`.
2. Instalar dependencias del puente si hiciera falta: `python3 -m pip install -r research/audit_bridge/requirements.txt`.
3. Regenerar los CSV y documentos con `export_audit_package.py` o un exportador equivalente documentado.
4. Ejecutar `validate_audit_package.py`.
5. Revisar que no haya datos sensibles.
6. Commit del paquete completo o, si es demasiado grande, commit de muestra representativa, manifest con hashes e instrucciones exactas de regeneracion.

## Auditoria automatizada robusta

El entrypoint recomendado para auditorias manuales, diarias y semanales es:

```bash
python research/audit_bridge/run_director_audit.py --cadence manual --audit-id <audit_id>
```

El runner siempre intenta escribir artefactos locales en:

```text
research/audit_bridge/requests/<audit_id>/
```

Como minimo deja `director_audit_run.json`, `director_audit_run.md`,
`internal_auditor_agent_review.json` e `internal_auditor_agent_review.md` incluso
si export, gate, validacion o entrega externa fallan antes de completar el ciclo.

La comprobacion de runtime Docker es informativa y no bloqueante. Usa
`docker compose ps --format json` y cae a `docker compose ps` si la salida JSON no
esta disponible. No depende de nombres fijos como `tradeo-backend` o
`tradeo-worker`; el campo estable es el servicio Compose (`backend`, `worker`,
`db`, `redis`, `frontend`). Si hay que usar compose files no estandar, definir:

```bash
TRADEO_AUDIT_COMPOSE_FILES=docker-compose.yml:docker-compose.audit.yml \
  python research/audit_bridge/run_director_audit.py --cadence daily
```

## Datos obligatorios

Todo paquete debe incluir, como minimo:

- `manifest.json` con metadatos legibles por maquina.
- `AUDIT_REQUEST.md` con resumen humano.
- `pattern_catalog.csv`, una fila por patron detectado.
- `pattern_events.csv`, una fila por ocurrencia independiente o por evento representativo exportado si el laboratorio aun no conserva todos los eventos.
- `paper_trades.csv`, una fila por trade paper generado por patrones.
- `ib_fills.csv`, una fila por fill de IB Paper, anonimizado.
- `experiment_registry.csv`, todas las variantes probadas, incluidas las descartadas.
- `metrics_by_pattern.csv`, `metrics_by_ticker.csv`, `metrics_by_period.csv`.
- `metrics_by_regime.csv` y `metrics_by_entry_variant.csv`, con rendimiento por bucket si hay closed paper trades o `empty_reason` si no hay datos.
- `director_gate_result.json`, generado antes de la validacion estricta del paquete.
- `code_references.md`.
- `config_snapshot/` con configuracion redacted usada para generar el paquete.
- `data_lineage.md`, `known_issues.md`, `audit_checklist.md`, `chatgpt_questions.md`, `reproducibility.md`.

## Datos que nunca deben subirse

No subir nunca:

- Claves, tokens, secrets, cookies, session IDs, passwords o credenciales.
- Account IDs reales de IB o identificadores de cuenta equivalentes.
- Informacion personal.
- Rutas locales sensibles.
- Hostnames privados si revelan infraestructura sensible.
- Order IDs o execution IDs sin hash.

Los tickers, fechas de mercado, resultados agregados y reglas de patron pueden mantenerse si no revelan datos sensibles, porque ChatGPT los necesita para auditar robustez.

## Reproducibilidad

Los exports deben ser reproducibles:

- Documentar comando exacto, rama, commit y entorno.
- Registrar fuente de datos y timeframes.
- Mantener hashes de archivos de datos cuando aplique.
- Indicar si el paquete es snapshot transaccional o export de API en caliente.

Todos los timestamps deben indicar zona horaria. Si el sistema solo guarda fechas diarias sin zona, el paquete debe normalizarlas y documentarlo en `data_lineage.md` o `known_issues.md`.

## Costes

Los costes deben mantenerse separados:

- `commission`
- `estimated_spread_cost`
- `estimated_slippage`
- `other_fees`

`net_pnl` debe calcularse como:

```text
gross_pnl - commission - estimated_spread_cost - estimated_slippage - other_fees
```

Si no hay trades paper o fills, los CSV correspondientes deben existir con cabecera y sin filas. Los breakdowns por regimen y entry variant deben seguir existiendo y explicar la ausencia de `closed_lab_trades`.
