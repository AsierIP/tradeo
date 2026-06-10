# Auditoría y mejora de Tradeo — Fable5, 2026-06-10

Rama: `fable5/tradeo-research-upgrade-20260610` → merge a `main`.
Alcance: auditoría completa (filosofía, arquitectura, research, datos, seguridad paper/live, automatización, observabilidad, tests, docs) + mejoras de alto impacto y bajo riesgo implementadas y verificadas.

## 1. Veredicto general

Tradeo está en un estado notablemente mejor de lo que su tamaño sugiere. La filosofía
("paper y validación estadística primero; live bloqueado por defecto") está implementada
de verdad, no solo declarada: la cadena Research → Lab → Director review → Producción →
Fox Hunter → Live tiene gates reales en código, con provenance de fills, manifiestos
firmados con caducidad, kill switch, límites duros de riesgo y triple confirmación para
armar live. Las auditorías previas (R1–R6) cerraron los huecos graves de evidencia.

Los puntos débiles reales no estaban en la seguridad de trading sino en la ingeniería
alrededor: **no había CI que ejecutara tests ni lint**, el frontend no tenía lockfile
(builds no reproducibles), y el pipeline de research consumía OHLCV sin un filtro de
calidad por símbolo (halts, feeds congelados, splits sin ajustar, huecos de calendario),
que es justo el tipo de ruido que envenena estadísticas de patrones en small caps.

## 2. Hallazgos por área

### Filosofía e intenciones — sólido
- Separación estricta de módulos: Research (descubre, nunca ejecuta), Laboratory
  (paper/shadow, nunca manda órdenes), Fox Hunter (solo patrones `production` con
  manifiesto válido). Research no puede marcar nada como `production`.
- Promoción cerrada con evidencia: ValidationGate estadístico (muestras, diversidad,
  expectancy, profit factor, p-value ajustado, walk-forward) → DirectorReviewGate
  (≥10 fills paper, ≥3 símbolos, PF ≥1.2) → manifiesto de producción firmado y con
  caducidad (90 días) → gate `live_armed` en tiempo de ejecución.

### Seguridad paper/live — sólido
- Live exige simultáneamente: `trading_mode=live`, `live_trading_enabled=true`,
  frase de confirmación correcta, kill switch apagado, `ibkr_readonly=false`,
  aprobación humana por señal y solo órdenes bracket con tope de valor (1.500 USD).
- Datos sintéticos prohibidos por validator (`allow_synthetic_market_data=False`).
- `.env` con credenciales **no está ni ha estado nunca en el historial de git**
  (verificado con `git log --all -- .env`); solo existe `.env.example`. El barrido
  inicial lo marcó como crítico por error: la contraseña vive solo en disco local.

### Calidad de datos — hueco corregido en esta rama
- `normalize_ohlcv`/`validate_ohlcv` ya rechazaban barras estructuralmente rotas
  (NaN, precios ≤0, high<low, índice desordenado/duplicado). Bien.
- Faltaba la capa siguiente: datos bien formados pero estadísticamente tóxicos.
  **Añadido `services/data_quality.py`** (ver §3).

### Automatización y observabilidad — correcto con huecos
- Scheduler APScheduler con 6+ jobs (scan, discovery, matching, lab, fox, director,
  reportes), watchdog que cierra discovery runs zombis, heartbeat del worker,
  endpoints `/health`, `/health/deep`, `/health/ibkr`.
- Huecos: el watchdog solo loguea (sin alerting), sin backup específico de PostgreSQL
  (solo tar de ficheros), sin rotación de logs/reportes. Ver roadmap §6.

### Tests y CI — hueco principal, corregido
- 109 tests pasaban en local, ruff limpio… pero **ningún workflow de CI los ejecutaba**:
  `director-audit.yml` solo valida paquetes de auditoría. Un push podía romper el
  backend sin que nada avisara. **Añadido `.github/workflows/ci.yml`** (ver §3).

### Frontend / UX — funcional, mejorable
- Dashboard único (`page.tsx`, ~990 líneas) con los tres módulos, embudo de señales,
  diagnósticos del Lab y near-misses. Cumple para operación personal.
- Sin lockfile → builds no reproducibles. **Corregido**: `package-lock.json` generado
  (fija Next 14.2.35, que además incorpora los fixes de seguridad de la serie 14.2.x).
- Pendiente (no bloqueante): ESLint sin configurar, sin vista de resultados de
  backtest, componente monolítico difícil de mantener. Ver roadmap.

### Código backend — bueno, con matices
- Tipado consistente, AuditLog en todas las acciones relevantes, config con 250+
  settings validados. Dos señalamientos del barrido inicial resultaron falsos
  positivos al revisarlos: el doble `research_hypothesis`/`research_hypothesis_package`
  es un alias intencional consumido por director_review_gate y el lab agent, y el
  `time.sleep(5)` del worker es el bucle de heartbeat.
- Matices reales que quedan: ~32 `except Exception  # noqa: BLE001` (enmascaran bugs),
  llamadas IBKR síncronas dentro de FastAPI (bloquean el event loop hasta 8 s), y
  umbrales mágicos sin justificar (p. ej. similitud 96% en dedupe de patrones).

## 3. Cambios implementados en esta rama

1. **Filtro de calidad de datos por símbolo** (`backend/tradeo/services/data_quality.py`):
   `assess_ohlcv_quality()` produce un `DataQualityReport` con métricas e issues:
   - `insufficient_bars` (menos de 60 barras por defecto)
   - `excess_zero_volume_bars` (>15% de barras sin volumen → halts/iliquidez)
   - `stale_close_run` (>8 cierres idénticos seguidos → feed congelado)
   - `calendar_gap` (>5 días hábiles sin barra, solo en `1d` → delisting/halt/datos rotos)
   - `suspect_split_or_bad_tick` (ratio close/close >4x o <0.25x → split sin ajustar)
   Cableado en `MarketScanner`: el símbolo se salta, se cuenta en el nuevo campo
   `ScanResponse.data_quality_skips` y queda registrado en `AuditLog` con acción
   `market_data_quality_reject` y el informe completo. Configurable vía settings
   `TRADEO_DATA_QUALITY_*` (documentados en `.env.example`); se puede desactivar con
   `TRADEO_DATA_QUALITY_FILTER_ENABLED=false`. El módulo es reutilizable desde el
   discovery lab y el entry scanner (siguiente paso natural, ver §6).
2. **CI real** (`.github/workflows/ci.yml`): en cada push a main y cada PR ejecuta
   ruff + pytest del backend (Python 3.12, `pip install -e ".[dev]"`) y build del
   frontend (Node 20, `npm ci` + `next build`).
3. **Lockfile del frontend** (`frontend/package-lock.json`): builds reproducibles y
   `npm ci` posible en CI; resuelve Next a 14.2.35.
4. **Tests**: `test_data_quality.py` con 11 tests (unitarios de cada issue + integración
   del scanner con AuditLog sobre SQLite en memoria).
5. **Higiene**: `pd.Timestamp.utcnow()` deprecado sustituido en fixtures (los avisos
   del suite bajan de 26 a 1).

## 4. Verificación

- `pytest`: **120 passed** (109 previos + 11 nuevos), 1 warning (externo, menor).
- `ruff check .`: limpio.
- `npm run build` (frontend): compila, mismas rutas y tamaños esperados.
- No ejecutado: mypy (no estaba en verde antes de esta rama y no es gate actual),
  tests E2E contra IBKR real (requieren TWS/Gateway activo).

## 5. Decisiones y supuestos

- No toqué umbrales de estrategia ni gates de promoción: cualquier cambio ahí debe
  salir de evidencia del Lab, no de una auditoría de código.
- Umbrales del filtro de calidad deliberadamente conservadores (ratio 4x no dispara
  con gaps reales de small caps de ±50–100%; solo splits/ticks rotos). Mejor pocos
  falsos positivos: cada rechazo queda auditado y es revisable.
- No añadí el filtro al discovery lab en esta pasada para mantener el diff revisable;
  el scanner era el punto de mayor exposición (alimenta señales operativas).
- El directorio untracked `research/audit_bridge/requests/TRADEO-AUDIT-...` pertenece
  al flujo de auditoría diaria de otro proceso: intacto y sin commitear.

## 6. Roadmap recomendado (orden de valor/esfuerzo)

1. Aplicar `assess_ohlcv_quality` también en `PatternDiscoveryLabAgent` y
   `PatternEntryScanner` (mismo módulo, ~20 líneas por sitio + tests).
2. Alerting del watchdog: un webhook/notificación cuando `repair()` actúe o un job
   falle N veces seguidas (hoy solo queda en logs).
3. Backup de PostgreSQL con `pg_dump` en `ops/scripts/backup_tradeo.sh` (hoy el tar
   no captura el volumen de la BD).
4. Sustituir los `except Exception` genéricos por jerarquía de excepciones propia,
   empezando por data provider y broker (donde más duele un error enmascarado).
5. Ejecutar llamadas IBKR en threadpool (`run_in_executor`) para no bloquear FastAPI.
6. Frontend: configurar ESLint, trocear `page.tsx` por módulo, vista de backtests.
7. mypy en verde e incorporarlo al CI como segundo gate.

— Fable5
