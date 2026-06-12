# P0 Infra/Execution — Alembic, agent_messages, spread snapshot (2026-06-12)

Implementa los tres puntos de infraestructura/ejecución del bloque **P0** del
`INFORME_MEJORA_TRADEO_V1_PRECISION` (§315): *Alembic inicial; tabla
`agent_messages`; snapshot de spread por señal (§3.3.1)*.

Rama: `fable5high/p0-infra-execution-20260611` sobre `main@7155999`.

## 1. Alembic inicial (§6.1, D-T1)

- Dependencia `alembic>=1.13.0` en `backend/pyproject.toml`.
- Árbol de migraciones: `backend/alembic.ini`, `backend/alembic/env.py`
  (URL resuelta desde `TRADEO_DATABASE_URL` vía `get_settings()`,
  `target_metadata = Base.metadata` para autogenerate futuro),
  `backend/alembic/versions/0001_baseline_schema.py`.
- Estrategia de adopción: la revisión baseline hace
  `Base.metadata.create_all(checkfirst=True)` — en DB nueva crea todo el
  esquema; en DB existente es no-op. `init_db()` ahora **stampa**
  `alembic_version = 0001_baseline` si la DB no tiene versión, de modo que
  cualquier despliegue arrancado queda adoptado y a partir de aquí
  `alembic upgrade head` es la ruta canónica de migración.
- Convención `schema_version` para blobs JSON: registro único en
  `backend/tradeo/db/json_contracts.py`. Cada columna JSON/JSONB persistida
  declara `{schema_version, validator}`. Los blobs legacy llevan validadores
  permisivos (`extra="allow"`, `strict=False`) — honesto: el contrato dice lo
  que hoy está garantizado. Los blobs nuevos (`agent_messages`) son estrictos.
  Helper `stamp_schema_version()` para escribir la versión dentro del blob.
- Test `test_json_contracts_have_version_and_validator` enumera las columnas
  JSON reales de `Base.metadata` y falla si alguna no está registrada (o si
  hay contratos huérfanos): añadir una columna JSON sin contrato rompe CI.

## 2. Tabla `agent_messages` (§5, plantilla de contrato de agentes puente)

- Modelo `AgentMessage` (`backend/tradeo/db/models.py`): `{id, agent,
  schema_version, produced_at_utc, input_refs, payload_json, severity
  (info|warning|critical|blocking), consumed_by, idempotency_key UNIQUE}`.
- Servicio `backend/tradeo/services/agent_messages.py`:
  - `publish_agent_message()` — **fail-closed**: payload validado por
    `AgentMessagePayloadV1` (Pydantic, `extra="forbid"`); inválido ⇒ raise,
    nada a la DB. **Idempotente**: misma key ⇒ devuelve la fila existente;
    misma key con contenido distinto ⇒ `AgentMessageContractError` (un
    productor con bug no puede pisar evidencia en silencio). Carrera de
    publicadores concurrentes resuelta vía unique constraint + relectura.
  - `pending_agent_messages()` / `mark_consumed()` — consumo por poll,
    `consumed_by` append-only e idempotente por consumidor.
  - `build_idempotency_key()` — sha256 de (agent, kind, partes de identidad).
- Los agentes publican **solo evidencia y bloqueos**; estados de promoción
  nunca se escriben por este bus (documentado en docstrings).
- Tests: `test_agent_messages_idempotent`, colisión de contenido, payload
  inválido rechazado antes de persistir, consumo por consumidor.

## 3. Snapshot de spread por señal (§3.3.1)

- Servicio `backend/tradeo/services/market_quotes.py`:
  - `IBKRQuoteSnapshotProvider` — un `reqMktData(snapshot=True)` por señal
    (contrato STK/SMART/USD cualificado), espera bid/ask hasta
    `signal_spread_snapshot_timeout_seconds`; el connect del broker queda
    acotado por ese mismo presupuesto (un TWS caído cuesta segundos por
    señal, no la ruta completa de órdenes). No coloca órdenes; funciona en
    sesión read-only.
  - `capture_signal_spread_snapshot()` — **fail-soft, nunca lanza**: registro
    autodescriptivo con `available`, `reason`, `bid/ask/last`, `mid`,
    `spread_abs`, `spread_observed_pct` (spread/mid) y `spread_cost_r`
    (spread / riesgo por acción). El KPI del informe (≥95% señales con
    snapshot) es medible desde los propios datos.
- Cableado en `PatternEntryScanner._store_signal()`: cada señal almacenada
  lleva `metadata_json["spread_snapshot"]` y
  `metadata_json["spread_observed_pct"]`. Proveedor inyectable
  (`scanner.quote_provider`) para tests/futuras fuentes.
- Honestidad de marcadores: un snapshot **no** es feed de microestructura.
  `execution_quality.MICROSTRUCTURE_FEED` sigue en `none_available`; el
  snapshot lleva su propio `data_basis = ibkr_quote_snapshot_at_signal` y
  repite `microstructure_feed = none_available`.
- Flags: `TRADEO_SIGNAL_SPREAD_SNAPSHOT_ENABLED` (default true),
  `TRADEO_SIGNAL_SPREAD_SNAPSHOT_TIMEOUT_SECONDS` (default 4). Añadidos a
  `.env.example`. En tests queda deshabilitado por conftest (no hay IBKR);
  los tests que lo ejercitan inyectan proveedor fake y activan el flag.

## Verificación

- `pytest tradeo/tests` → **333 passed, 1 skipped** (las 18 nuevas incluidas)
  con el venv de `/home/vboxuser/tradeo/backend/.venv` (alembic 1.18.4
  instalado en ese venv para poder ejecutar las pruebas localmente).
- `ruff check .` → limpio.
- `alembic upgrade head` sobre sqlite temporal crea exactamente las tablas de
  `Base.metadata` + `alembic_version` (test); sobre DB ya creada con
  `create_all` es no-op + stamp (test).

## Pendientes / riesgos conocidos

- El snapshot abre y cierra una conexión IBKR por señal. Con pocas señales
  por scan es aceptable; si el volumen crece, batched snapshots o conexión
  compartida del scan serían la mejora siguiente.
- Cobertura del KPI ≥95%: medirla en producción requiere TWS/Gateway activo
  durante los scans de Lab; el campo `reason` permite auditar por qué falta.
- Docker: la imagen del backend necesita rebuild para incluir `alembic`
  (nueva dependencia) y los nuevos módulos. `init_db()` stampa el baseline en
  el primer arranque tras el deploy.
- Los validadores estrictos para blobs legacy (p. ej. `signals.metadata_json`)
  quedan para una iteración posterior: subir `schema_version` y endurecer el
  validador columna a columna.
