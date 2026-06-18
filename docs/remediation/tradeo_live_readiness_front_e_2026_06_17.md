# Tradeo live readiness audit - Frente E (2026-06-17)

## Summary

Live no esta listo. Hay buenas defensas en Fox/Director, brackets IBKR,
reconciliacion y dashboard operativo, pero existe un bypass manual critico que
permite enviar live desde senales que no vienen de Fox/production manifest. Los
otros bloqueos principales son riesgo acumulado no fiable, readiness que puede
marcar "allowed" sin comprobar broker/live-port/reconciliacion fresca, y monitor
post-promocion que no corta con fills live.

## Findings

### P0

- `backend/tradeo/routers/signals.py:20` + `backend/tradeo/services/ibkr_broker.py:274` + `backend/tradeo/routers/ibkr.py:80` - Bypass de DirectorProductionGate por submit manual. `human-approve` marca `human_approved=true` en cualquier senal y una `paper_approved` queda ejecutable; `IBKRBroker` acepta `PAPER_APPROVED` o `LIVE_APPROVED` si hay aprobacion humana, sin validar `entry_module=fox_hunter`, estado `production`, manifest activo ni hash de evidencia. En live armado, una senal Lab/legacy puede acabar en `/ibkr/signals/{id}/submit-bracket` como `LIVE_ORDER`.
- `backend/tradeo/services/supervisor.py:33` + `backend/tradeo/services/scanner.py:25` - El scanner legacy sigue pudiendo crear senales `pending_human_approval` cuando `live_armed=true`, fuera del flujo Fox/manifest. Combinado con el punto anterior, abre live sin evidencia suficiente.

### P1

- `backend/tradeo/services/risk_manager.py:33` + `backend/tradeo/services/risk_manager.py:75` + `backend/tradeo/services/risk_manager.py:94` + `backend/tradeo/services/reconciliation.py:596` - Riesgo live no esta broker-synced. Equity/cash salen de capital configurado + `RiskLedger`, pero el cierre reconciliado solo actualiza `Trade.pnl_usd/r_multiple`; no se ve actualizacion del ledger ni de equity desde IBKR. El limite diario puede no disparar tras perdidas reales y el limite de gross exposure mira solo el nuevo notional, no exposicion acumulada.
- `backend/tradeo/modules/shared/entry_scanner.py:660` + `backend/tradeo/modules/shared/entry_scanner.py:821` + `backend/tradeo/services/ibkr_broker.py:302` + `backend/tradeo/services/ibkr_broker.py:423` - `live_orders_allowed` puede ser falso positivo: no incluye `ibkr_readonly=false`, puerto live, cuenta IBKR explicita, allowlist, manifest elegible ni reconciliacion fresca. Ademas, en `trading_mode=live` con puerto paper, el broker no exige puerto live y etiqueta la orden como `LIVE_ORDER`.
- `backend/tradeo/tasks/worker.py:395` + `backend/tradeo/tasks/worker.py:413` - El worker agenda Fox al minuto y reconciliacion cada 30 min, pero no ejecuta reconciliacion inicial antes de escaneres con ordenes. Tras restart con divergencia DB/broker, hay ventana para nuevas ordenes antes del auto-kill.
- `backend/tradeo/services/pattern_health_monitor.py:71` + `backend/tradeo/services/evidence.py:53` + `backend/tradeo/research/novel_pattern_matcher.py:75` + `backend/tradeo/modules/fox_hunter/production_manifest.py:62` - El monitor post-promocion cuenta solo `ibkr_paper_fill`; `live_fill` queda fuera. Ademas matcher/manifest no bloquean `drift_status=decaying`, pese al comentario de config. La degradacion live puede no cerrar el grifo.
- `backend/tradeo/routers/risk.py:15` + `backend/tradeo/routers/health.py:15` + `backend/tradeo/routers/health.py:50` + `backend/tradeo/services/watchdog.py:24` - Observabilidad de kill/readiness incompleta. `/risk/kill-switch` solo registra intencion y pide editar `.env`; `/health` y `/health/deep` no exponen runtime kill switch, worker age, ultimas reconciliaciones ni fallos de jobs. El runbook pide verificar runtime kill por health, pero esos endpoints no lo muestran.

### P2

- `backend/tradeo/modules/shared/entry_scanner.py:104` + `backend/tradeo/modules/shared/entry_scanner.py:1007` + `backend/tradeo/modules/shared/entry_scanner.py:1978` - Con runtime kill activo, Lab degrada a shadow, pero Fox no prebloquea igual: puede crear senal live-approved y dejar que el broker falle. No mueve dinero, pero ensucia trazabilidad.
- `backend/tradeo/services/ibkr_broker.py:547` - `repair_trade_exit_protection` es paper-only, pero no comprueba runtime kill switch; si se habilita auto-repair, podria colocar OCA paper durante un kill runtime previo.
- `backend/tradeo/services/ibkr_broker.py:232` + `backend/tradeo/services/ibkr_broker.py:384` - Si IBKR devuelve multiples cuentas y `TRADEO_IBKR_ACCOUNT` no esta fijado, las ordenes pueden salir sin `order.account`. Para live debe ser hard gate.
- `backend/tradeo/core/config.py:318` + `backend/tradeo/services/ibkr_broker.py:278` - `TRADEO_IBKR_ALLOWED_SYMBOLS` vacio significa allow-all. Para un piloto live deberia ser allowlist obligatoria.
- `frontend/app/page.tsx:811` + `backend/tradeo/services/ops_alerts.py:24` - El frontend no consume `/health/deep`, reconciliacion ni `internal_ops_alert`; Asier ve modulos y fills, pero no una vista unica de abort conditions.

## Mejoras concretas para live readiness

- Crear `LiveReadinessGate` unico y usarlo en health, Fox status y submit IBKR: bloquea si falta manifest Fox, live port/cuenta/allowlist, readonly=false, runtime/env kill off, worker fresco, reconciliacion limpia reciente, IBKR account OK y credenciales no-default.
- Separar submit paper/live. En live aceptar solo `LIVE_APPROVED` de `entry_module=fox_hunter` con `production_manifest_status(valid)` y hash vigente; rechazar siempre `PAPER_APPROVED`.
- Sincronizar RiskManager con broker/ledger: NetLiquidation/AvailableFunds, PnL diario/mensual de fills reales, exposicion acumulada DB+broker open orders/positions.
- Ejecutar reconciliacion en arranque antes de Fox y persistir `last_clean_reconciliation_at`; si esta ausente/stale, `live_orders_allowed=false`.
- Extender health monitor a `live_fill`, bloquear `drift_status in {decaying,degrading,regressing,deteriorating}` en matcher/manifest y mostrar CUSUM live de R/slippage/comision.
- Anadir panel superior "Live readiness" en frontend: kill env/runtime, live armed, readonly, puerto, cuenta, allowlist, worker age, last reconcile, DB vs broker diff, manifests elegibles, fills normales/degraded, coste/slippage coverage.

## Tests/runbook checks recomendados

- Test: `/ibkr/signals/{id}/submit-bracket` en live rechaza senales `paper_approved`, Lab, legacy o sin manifest Fox valido.
- Test: `live_orders_allowed=false` con readonly true, puerto paper, cuenta vacia, allowlist vacia, worker stale o reconciliacion stale.
- Test: RiskManager dispara daily/monthly loss y gross exposure acumulada usando trades cerrados reconciliados y open orders.
- Test: worker ejecuta reconciliacion limpia antes de permitir Fox live tras restart.
- Test: `live_fill` alimenta health monitor y `drift_status=decaying` impide nuevos matches Fox.
- Runbook: antes de live correr health/readiness, IBKR account, positions/open-orders, reconcile clean, what-if, kill-switch drill, una orden min-size paper, export audit package y validacion Director.
