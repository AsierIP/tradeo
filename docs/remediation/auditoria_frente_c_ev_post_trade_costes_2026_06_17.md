# Auditoria Frente C - EV/post-trade/costes - 2026-06-17

## Summary

La arquitectura separa bastante bien Research, shadow observations, IBKR paper fills y production gate. Los gates fuertes no deberian aprobar produccion sin fills IBKR, comisiones y EV ajustado. Aun asi, hay riesgos materiales para EV/live readiness:

- P0: los partial fills pueden cerrarse usando cantidad ejecutada, pero PnL/R se calculan con la cantidad solicitada.
- P1: ranking/learning usa historial de fills con `trade.r_multiple` bruto, no neto de comision/costes.
- P1: audit export resume fills en filas sinteticas y ademas lee un overview limitado, por lo que no audita todos los fills ni parciales reales.
- P1: costes de spread/slippage pueden quedar como `0.0` por defecto y aun pasar controles de "campo presente".
- P1/P2: borrow/locate de shorts no esta capturado post-trade salvo `other_fees` manual.
- P2: dashboard/report legacy publican PnL/R bruto o mezclado, aunque la UI nueva tambien muestra `Net R`.

## Findings

### P0 - Partial fills cerrados con PnL/R sobre `trade.qty` solicitado

Referencias:

- `backend/tradeo/services/reconciliation.py:596`: cierra si `exit_leg["qty"] >= min(abs(trade.qty), entry["qty"])`.
- `backend/tradeo/services/reconciliation.py:602`: calcula `gross_pnl` con `abs(float(trade.qty or 0))`.
- `backend/tradeo/services/reconciliation.py:605`: calcula `r_multiple` con denominador `risk_per_share * abs(trade.qty)`.
- `backend/tradeo/services/implementation_shortfall.py:146`: comision R tambien usa `qty = abs(int(trade.qty or 0))`.

Impacto:

Si una orden pide 10, entra 5 y sale 5, el trade queda cerrado correctamente sobre los 5 ejecutados, pero PnL/R se calculan sobre 10. Eso infla o deforma EV, drawdown, profit factor, ranking, dashboard y Director gates. Tambien subestima `commission_r` si el denominador usa cantidad solicitada en lugar de cantidad ejecutada.

Patch recomendado:

- Persistir `executed_qty = min(entry_fill_qty, exit_fill_qty)` para cierre realizado.
- Calcular `gross_pnl`, `pnl_usd`, `r_multiple`, `return_pct`, `commission_r` y exposure con `executed_qty`.
- Guardar `requested_qty`, `entry_fill_qty`, `exit_fill_qty`, `closed_qty`, `partial_fill_closed=true` y `remaining_qty` cuando aplique.
- No marcar `CLOSED` si queda posicion viva no protegida; cerrar lote ejecutado o crear child trade/position lot para remanente.

Tests exactos:

- `backend/tradeo/tests/test_execution_state_transitions.py::test_reconciliation_partial_entry_exit_uses_executed_qty_for_pnl_and_r`
- `backend/tradeo/tests/test_execution_quality_audit.py::test_execution_adjusted_r_commission_uses_executed_qty_not_requested_qty`
- Caso: `qty=10`, entry fill `5 @ 10`, exit fill `5 @ 14`, risk/share `1`. Esperado `pnl_usd=20`, `r_multiple=4`, no `40/4` sobre 10.

### P1 - Lab learning/ranking aprende de R bruto, no EV neto

Referencias:

- `backend/tradeo/modules/shared/entry_scanner.py:1552`: carga historial de trades cerrados.
- `backend/tradeo/modules/shared/entry_scanner.py:1574`: filtra evidencia IBKR paper fill fuerte.
- `backend/tradeo/modules/shared/entry_scanner.py:1592`: agrega `float(trade.r_multiple or 0.0)`.
- `backend/tradeo/modules/shared/entry_scanner.py:1932`: `_history_item` calcula expectancy/profit factor desde esos R.
- `backend/tradeo/services/opportunity_ranking.py:83`: usa `history_score`.
- `backend/tradeo/services/opportunity_ranking.py:106`: pondera `execution_history` al 34% si hay historial.

Impacto:

El ranking operativo puede priorizar oportunidades con historial paper positivo bruto aunque el neto sea negativo por comision/costes. Esto afecta seleccion de trades, EV esperado mostrado como `paper_history` y readiness para escalar de laboratorio a paper/live.

Patch recomendado:

- En `_execution_history`, usar `trade_execution_adjusted_r(trade)["net_r"]` cuando exista.
- Excluir o degradar filas sin cobertura neta completa.
- Guardar `r_basis="execution_adjusted_net_r"` en `opportunity_rank_components`.

Tests exactos:

- `backend/tradeo/tests/test_pattern_entry_scanner.py::test_execution_history_uses_net_r_for_opportunity_rank`
- `backend/tradeo/tests/test_opportunity_ranking.py::test_paper_history_negative_net_r_penalizes_rank`

### P1 - Audit export no exporta fills reales completos y queda limitado por overview

Referencias:

- `research/audit_bridge/export_audit_package.py:403`: lee `/laboratory/overview`.
- `backend/tradeo/routers/laboratory.py:25`: endpoint sin parametro de auditoria.
- `backend/tradeo/services/module_dashboard.py:26`: `module_overview(..., limit=80)`.
- `backend/tradeo/services/module_dashboard.py:39`: query base limitada a 500 y luego recortada.
- `research/audit_bridge/export_audit_package.py:1168`: itera `laboratory_overview["trades"]`.
- `research/audit_bridge/export_audit_package.py:1179`: crea una fila ENTRY sintetica.
- `research/audit_bridge/export_audit_package.py:1183`: crea una fila EXIT sintetica.
- `research/audit_bridge/export_audit_package.py:1209`: usa `trade.qty` como cantidad de cada fill.
- `research/audit_bridge/export_audit_package.py:1211`: copia la misma comision agregada en cada fila sintetica.

Impacto:

`ib_fills.csv` no es "una fila por fill IBKR"; es maximo entry/exit por trade y puede duplicar comision a nivel fill, ocultar partial fills, precios parciales, timestamps multiples y liquidez por fill. Al depender de `/laboratory/overview`, el paquete puede omitir trades/fills antiguos o fuera del top 80/500. Eso rompe sample-size/effective fills, auditoria de parciales y confianza del Director.

Patch recomendado:

- Crear endpoint/servicio de audit export que consulte DB directamente o `/laboratory/audit-fills?limit=...&since=...`, sin limite de dashboard.
- Exportar cada elemento de `trade.metadata_json["ibkr_fills"]` como fila de `ib_fills.csv`.
- `paper_trades.csv` debe reconciliar `quantity=sum(entry fills)=sum(exit fills)=closed_qty`.
- Separar `trade_count`, `fill_count`, `closed_qty`, `requested_qty`.

Tests exactos:

- `backend/tradeo/tests/test_audit_hardening.py::test_export_ib_fills_preserves_multiple_partial_fill_rows`
- `backend/tradeo/tests/test_audit_hardening.py::test_export_audit_uses_unbounded_audit_source_not_dashboard_overview_limit`
- `research/audit_bridge/validate_audit_package.py` test: suma de quantities por leg debe reconciliar con `paper_trades.quantity`.

### P1 - Spread/slippage pueden pasar como cero por defecto sin captura real

Referencias:

- `backend/tradeo/services/reconciliation.py:626`: si falta `estimated_spread_cost`, se pone `0.0`.
- `backend/tradeo/services/reconciliation.py:628`: si falta `estimated_slippage`, se pone `0.0`.
- `backend/tradeo/services/reconciliation.py:630`: `spread_cost_source="not_captured_zero_default"`.
- `research/audit_bridge/export_audit_package.py:1107`: exporta `estimated_spread_cost`.
- `research/audit_bridge/export_audit_package.py:1108`: exporta `estimated_slippage`.
- `research/audit_bridge/director_gate.py:494`: solo revisa que `commission` y `estimated_spread_cost` no esten vacios.
- `research/audit_bridge/director_gate.py:499`: solo revisa que `estimated_slippage` no este vacio.

Impacto:

Un cero por defecto satisface presencia de campo aunque la fuente diga que no fue capturado. El audit contract exige costes separados y recalculables; esto puede convertir "dato ausente" en "coste cero", sobrestimando EV neto o dando falsa readiness.

Patch recomendado:

- No defaultar spread/slippage faltantes a `0.0` para evidencia fuerte; usar `None`/campo vacio y `*_missing=true`.
- Si se usa cero, requerir `*_source` distinto de `not_captured_zero_default` para pasar Director/audit.
- Director/audit debe bloquear `source=not_captured_zero_default` salvo modo explicitamente "realized fills already include this cost".

Tests exactos:

- `backend/tradeo/tests/test_execution_state_transitions.py::test_missing_spread_slippage_defaults_do_not_count_as_reconciled_costs`
- `backend/tradeo/tests/test_audit_hardening.py::test_director_gate_blocks_zero_default_cost_sources`

### P1 - Shorts: borrow/locate no esta reconciliado post-trade

Referencias:

- `backend/tradeo/services/ibkr_broker.py:259`: shorts se permiten con `allow_shorts`.
- `backend/tradeo/services/ibkr_broker.py:390`: setea `shortSaleSlot=1`, pero no captura locate/borrow.
- `backend/tradeo/research/reward_risk_analyzer.py:257`: Research si suma `short_borrow_proxy_pct`.
- `research/audit_bridge/export_audit_package.py:189`: campos de PnL no incluyen `borrow_cost`.
- `research/audit_bridge/export_audit_package.py:1109`: solo lee `other_fees`.

Impacto:

Research penaliza shorts con proxy, pero post-trade/audit no captura borrow real ni locate fees. En small caps/shorts esto puede cambiar EV neto y readiness. Si se meten manualmente en `other_fees`, no hay fuente ni contrato especifico.

Patch recomendado:

- Agregar `borrow_cost`, `locate_fee`, `borrow_rate`, `borrow_days`, `borrow_source`.
- Para shorts, bloquear promotion si no hay `borrow_not_applicable_reason` o `borrow_cost_source`.
- Mapear fees IBKR/statement import a esos campos cuando existan.

Tests exactos:

- `backend/tradeo/tests/test_audit_hardening.py::test_short_paper_trade_requires_borrow_or_not_applicable_provenance`
- `backend/tradeo/tests/test_director_review_gate.py::test_short_production_gate_blocks_missing_borrow_cost_provenance`

### P2 - Exit reason puede inferirse por precio cercano y contaminar slippage_R

Referencias:

- `backend/tradeo/services/reconciliation.py:460`: `_exit_reason_for_fill`.
- `backend/tradeo/services/reconciliation.py:471`: target por order id.
- `backend/tradeo/services/reconciliation.py:473`: stop por order id.
- `backend/tradeo/services/reconciliation.py:475`: si no hay ids, compara distancia a target/stop.
- `backend/tradeo/services/implementation_shortfall.py:78`: `exit_reason` decide salida teorica.
- `backend/tradeo/services/implementation_shortfall.py:83`: reason desconocido se trata como time/zero exit shortfall.

Impacto:

Una salida manual, time stop, cancel/replace o fill sin ids puede quedar etiquetada como target/stop por cercania. Eso no cambia PnL realizado, pero si cambia implementation shortfall y diagnosticos de bracket outcome.

Patch recomendado:

- Usar `unknown_exit_fill` o `manual_exit` cuando no haya order id/perm id de bracket.
- No inferir target/stop por precio para evidencia fuerte; marcar `exit_reason_inferred=true` y excluir de slippage gate o degradar.

Tests exactos:

- `backend/tradeo/tests/test_execution_state_transitions.py::test_exit_reason_without_bracket_identity_is_inferred_and_degraded`
- `backend/tradeo/tests/test_execution_quality_audit.py::test_unknown_exit_reason_does_not_fake_target_shortfall`

### P2 - Dashboard/report legacy siguen publicando PnL/R bruto

Referencias:

- `backend/tradeo/services/module_dashboard.py:153`: `_pnl_points` acumula `trade.pnl_usd`.
- `backend/tradeo/services/module_dashboard.py:371`: trade payload publica `pnl_usd`.
- `backend/tradeo/services/module_dashboard.py:449`: tambien publica `gross_r`; `net_r` va separado.
- `frontend/app/page.tsx:675`: KPI "PnL fills" usa `stats.total_pnl_usd`.
- `frontend/app/page.tsx:702`: columna PnL usa `t.pnl_usd`.
- `backend/tradeo/services/metrics.py:10`: `refresh_pattern_metrics` toma todos los closed trades.
- `backend/tradeo/services/metrics.py:16`: usa `t.r_multiple` sin filtro de evidencia/coste neto.
- `backend/tradeo/schemas.py:84`: `TradeOut` legacy no tiene evidencia ni costes.
- `backend/tradeo/services/reports.py:198`: report pack omite evidencia/costes en trades.

Impacto:

El operador ve `Net R`, pero los elementos visuales principales de PnL y rutas legacy pueden seguir siendo brutos o mezclados con shadow si se refrescan metricas legacy. Esto no deberia alimentar gates, pero si puede afectar decisiones humanas.

Patch recomendado:

- Renombrar `pnl_usd` visible a `gross_pnl_usd`.
- Agregar `net_pnl_usd`, `pnl_basis`, `cost_coverage` en schemas legacy y report pack.
- `refresh_pattern_metrics` debe filtrar evidencia fuerte y usar net R ajustado.

Tests exactos:

- `backend/tradeo/tests/test_module_dashboard.py::test_operational_pnl_points_use_net_pnl_when_cost_coverage_complete`
- `backend/tradeo/tests/test_json_contracts.py::test_dashboard_trade_schema_exposes_gross_net_and_basis`

### P2 - Market replay re-penaliza spread/slippage sobre coste base

Referencias:

- `backend/tradeo/research/window_sampler.py:248`: `execution_cost_r` incluye spread/slippage/gap.
- `backend/tradeo/research/reward_risk_analyzer.py:224`: el triple barrier resta `execution_cost_r`.
- `backend/tradeo/research/market_replay.py:154`: calcula otra vez `spread_slippage_pct`.
- `backend/tradeo/research/market_replay.py:168`: suma `spread_slippage_r * 0.50` como `extra_cost`.

Impacto:

Es conservador, pero mezcla EV base neto con stress adicional. Puede rechazar edges buenos y dificulta comparar "base cost", "cost x2/x3" y "late/partial replay". No infla readiness, pero reduce trazabilidad.

Patch recomendado:

- Separar `base_cost_r`, `latency_penalty_r`, `additional_spread_stress_r`.
- Etiquetar `expected_expectancy_r` como `stress_expectancy_r` si incluye penalizacion adicional.

Tests exactos:

- `backend/tradeo/tests/test_autonomous_research_lab.py::test_market_replay_reports_base_cost_and_extra_stress_separately`

## Recomendaciones de implementacion

1. Prioridad inmediata: arreglar contabilidad por `executed_qty` en reconciliacion y implementation shortfall.
2. Cambiar history/ranking a `net_r` con cobertura completa, y bajar score si falta cobertura.
3. Rehacer audit export para usar fuente DB/audit dedicada y exportar fills atomicos reales.
4. Endurecer provenance: missing cost != zero cost.
5. Añadir contrato short-borrow antes de permitir promotion de shorts.
6. Limpiar superficies legacy: gross/net/basis explicitos en API, dashboard y report pack.

## Cobertura revisada

No se modifico codigo de runtime. Auditoria estatica sobre repo y tests existentes. No se tocaron `.env`, live config ni `research/audit_bridge/requests/*`.
