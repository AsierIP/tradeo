# Auditoria Tradeo V 0.9 preLive

Fecha: 2026-06-17
Repositorio auditado: `/home/vboxuser/tradeo`, rama `main`, HEAD local `8ebb7a7`
Paquete de auditoria principal: `research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal`

## 1. Dictamen Ejecutivo

**Tradeo va por el buen camino para operar en Research/Lab/Paper de forma prudente, pero no esta listo para Live en los proximos dias.**

Valoracion global preLive: **38/100 - ROJO para Live**.

La arquitectura ha avanzado mucho desde los informes de Fable5Max: hay separacion Research -> Lab -> Director -> Production -> Fox, gates de evidencia, `fill_provenance`, manifiestos de produccion, FDR/DSR/n_eff, matching conformal y bloqueo fuerte de live. El problema ya no es que el sistema este indefenso; el problema es que **la evidencia operativa real todavia no existe**.

El ultimo paquete Director esta bloqueado:

- `paper_trades.csv` tiene 0 filas de datos.
- `ib_fills.csv` tiene 0 filas de datos.
- Hay 0 fills IBKR Paper contables por Director.
- Hay 3 patrones con estados promovidos/offenders sin fills enlazados.
- `nested_discovery_replay` no ha pasado en 2995 filas de experimento.
- Quedan 271 filas con contrato anti-lookahead en blanco.
- Quedan 125/5619 eventos repetidos por `duplicate_group_id`.

Evidencia: `research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal/director_gate_result.md:7` y `manifest.json:12`.

**Decision Go/No-Go:** No-Go para Live. Go condicionado para seguir en **Lab/IBKR Paper** si se mantiene `paper`, `live_armed=false`, kill switch sano, puerto IBKR paper y entorno no expuesto publicamente.

## Addendum Release Evidence 2026-06-17

Este informe queda enlazado al runbook operativo:
`docs/remediation/prepaper_operational_runbook_2026_06_17.md`.

Estado verificado del paquete
`research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal`:

- `python3 research/audit_bridge/validate_audit_package.py ...`: `AUDIT PACKAGE OK`.
- `python3 research/audit_bridge/director_gate.py ... --allow-blocked-exit-zero`:
  `DIRECTOR GATE BLOCKED`.
- `sha256sum -c file_hashes.sha256`: todos los archivos del paquete listados
  reportan `OK`.
- `file_hashes.sha256`:
  `b897d400b32697740c1de4311d367812cb9228e577399aeb401d4f0b73327711`.

El target no mutante para repetir esas comprobaciones es:

```bash
make prepaper-verify \
  AUDIT_PACKAGE=research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
```

La conclusion operativa no cambia: **Live bloqueado; Paper ampliado y medido**.
El paquete es reproducible y auditable, pero no promociona patrones porque tiene
0 paper trades, 0 IBKR Paper fills y Director gate `blocked`.

## 2. Coordinacion De Los 3 Agentes

| Agente | Foco | Dictamen |
|---|---|---|
| Gauss | Research, datos, PIT, automejora | Buen camino tecnico, pero no Live: PIT/delistings pendiente, nested replay sin pasar, sin fills paper. |
| Linnaeus | Lab, Director, Fox, ejecucion | Separacion y gates implementados; falta prueba real reconciliada con fills IBKR Paper. |
| Dewey | Operacion, config, CI, exposicion | 38/100; Live rojo. Riesgo adicional si frontend/backend quedan expuestos fuera de localhost/VPN. |

Los tres coinciden en el punto central: **la seguridad de bloqueo esta bastante bien; la evidencia para Live no esta.**

## 3. Semaforo Por Area

| Area | Estado | Valoracion | Comentario |
|---|---:|---:|---|
| Research tecnico | Ambar/verde | 6/10 | Validacion estadistica, n_eff, FDR/DSR, costes, HDBSCAN/prototipos y auditoria han mejorado. Aun hay contratos no convertidos en evidencia limpia. |
| Research evidencia | Rojo | 4/10 | El paquete sigue bloqueado por `nested_discovery_replay`, duplicados y anti-lookahead blanks. |
| Datos/PIT | Rojo | 3/10 | PIT/delistings siguen explicitamente no disponibles; mitigacion honesta con cap, no solucion. |
| Lab/Paper | Ambar | 6/10 | Paper puede correr con safety gates, pero no hay fills cerrados Director-countable. |
| Director/Production | Rojo | 4/10 | Gate duro implementado, pero sin 30 fills, sin evidencia packet pasado y sin replay. |
| FoxHunter/Live | Rojo | 4/10 | Live esta correctamente bloqueado: 0 patrones production, 0 manifests activos, `auto_submit_live_orders=false`. |
| Ejecucion/reconciliacion | Ambar | 6/10 | Hay `fill_provenance`, reconciliation y slippage tooling; falta E2E real de Paper. |
| Operacion/CI | Ambar | 5/10 | CI basico existe; el paquete reciente esta untracked y el workflow Director valida un paquete fijo/antiguo. |
| Seguridad exposicion | Ambar/Rojo | 4/10 | Correcto si es localhost/VPN. Rojo si `8000`/`3000` quedan expuestos a red no confiable. |

## 4. Matriz De Puntos Fable5Max

| Punto de mejora | Estado | Valoracion preLive |
|---|---:|---|
| P0-1 pseudo-replicacion: dedup + n_eff | Implementado/parcial | `quant_validation.py` tiene dedup y unicidad media; el paquete exportado aun muestra duplicados a resolver. |
| P0-2 multiplicidad: BH-FDR + DSR + ledger | Implementado/parcial | Settings y registry existen; `GlobalExperimentRegistry` ya exporta hashes, pero la evidencia sigue bloqueada por replay y active blockers. |
| P0-3 vela viva / barras completas | Implementado | `discovery_match_complete_bars_only=True`; matcher evita vela diaria incompleta. |
| P0-4 umbral global de matching | Implementado/parcial | Umbral por patron, conformal kNN/Mahalanobis y floor global existen. Patrones antiguos sin `prototype_bank` caen a legacy hasta rediscovery. |
| P0-5 PIT/delistings | Pendiente | `universe_point_in_time_available=false`, `universe_delisting_data_available=false`. Live/produccion no deberia apoyarse en claims historicos sin PIT. |
| P0-6 outcomes/costes/fills pesimistas | Implementado/parcial | Triple barrera canonica y cost stress existen; falta comprobar ejecucion real con fills, comisiones y slippage. |
| P0-7 n=10 Director | Implementado | 10 fills es solo review trigger; produccion exige DirectorProductionGate. |
| P0-8 scheduler discovery diario | Implementado | `discovery_scan_minutes=1440`; evita reruns intradia sobre la misma barra diaria. |
| Meta-labeling calibrado | Parcial | Existe contrato/calibracion y leak guard, pero no predictor OOS operativo ni gate Lab con `p_meta`. |
| kNN/Mahalanobis/conformal | Implementado/parcial | Infra implementada; requiere rediscovery fresca y evidencia FPR/fills para decision operativa. |
| DTW / shape verifier | Parcial | Diagnostico implementado, hard gate off por defecto hasta contratos frescos. |
| False-match harness | Parcial | Harness existe; shadow-occurrences reales y DriftSentinel completo siguen pendientes. |
| HDBSCAN + consenso | Parcial | HDBSCAN/consenso disponibles; fallback conservador; paquete actual aun tiene muestras/concentracion debiles. |
| Fix grid automejora | Implementado | Se corrigio truncado lexicografico con `sample_grid` estratificado y cobertura por eje. |
| ExperimentOrchestrator | Parcial | Planifica/accounting multi-espacio; no ejecuta todavia evaluadores end-to-end de todos los espacios. |
| Champion/challenger | Parcial | Manifiestos y helpers paper/shadow existen; falta ciclo real con evidencia. |
| Puentes/agentes | Parcial | `agent_messages`, execution quality, reconciliation y regime tooling existen; no todos los agentes del informe estan cerrados como procesos completos. |
| Alembic / schema version | Parcial | Baseline Alembic existe; `init_db` mantiene compatibilidad/ad-hoc drift. |
| IBKR async/aislado | Parcial | Hay hardening documentado; no se verifico runtime con tests en esta auditoria. |
| Dashboard honesto | Implementado | Separa shadow/order/fill y declara que no es fuente Director. |
| Live bloqueado por defecto | Implementado | Defaults conservadores y `live_armed` exige modo live, flag, frase exacta y kill switch apagado. |

## 5. Evidencia Tecnica Relevante

- Defaults conservadores: `trading_mode="paper"`, `live_trading_enabled=false`, `kill_switch_enabled=false` en `backend/tradeo/core/config.py:34`.
- `live_armed` solo se activa con modo live, flag, frase exacta y kill switch apagado: `backend/tradeo/core/config.py:425`.
- PIT/delistings no disponibles: `backend/tradeo/core/config.py:81`.
- Discovery diario/post-close y RR reducido a `2.5,4.0`: `backend/tradeo/core/config.py:120`.
- n_eff, FDR y DSR configurados: `backend/tradeo/core/config.py:142`.
- Matching sin vela viva y umbral por patron: `backend/tradeo/core/config.py:181`.
- Conformal kNN/Mahalanobis habilitado cuando el patron tiene `prototype_bank`: `backend/tradeo/core/config.py:206`.
- Ambiguedad con dientes habilitada: `backend/tradeo/core/config.py:230`.
- Paper Lab permitido con safety gates; live Fox requiere `auto_submit_live_orders` y `live_armed`: `backend/tradeo/modules/shared/entry_scanner.py:600`.
- FoxHunter exige `production` + manifest valido: `backend/tradeo/modules/fox_hunter/production_manifest.py:54`.
- `DirectorProductionGate` exige 30 paper fills y contratos cientificos: `backend/tradeo/services/director_review_gate.py:826`.
- Evidence taxonomy y fill provenance fuerte: `backend/tradeo/services/evidence.py:6`.
- Solo `broker_execution` o `broker_statement_import` son provenance real: `backend/tradeo/services/evidence.py:56`.
- Prototype bank con split-conformal: `backend/tradeo/research/prototype_bank.py:1`.
- Triple barrera con fills pesimistas: `backend/tradeo/research/quant_validation.py:162`.
- Paquete del 16/06: 500 patterns, 5619 events, 0 paper trades, 0 IB fills: `research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal/manifest.json:12`.
- Director gate bloqueado: `research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal/director_gate_result.md:5`.

## 6. Bloqueantes No-Go Live

1. **Cero fills paper reales.** Sin `ibkr_paper_fill` cerrado no hay comisiones, slippage, fill timestamps, execution hashes ni validacion de coste.
2. **Director gate bloqueado.** El paquete actual no permite aprobar ningun patron mas alla de research/watchlist.
3. **Nested discovery replay no pasado.** El contrato existe, pero `nested_replay_passed_rows=0` en el paquete.
4. **PIT/delistings pendiente.** El sesgo de supervivencia esta reconocido y mitigado con cap, pero no resuelto con vendor.
5. **Patrones promovidos legacy/offenders.** `PATTERN_000282`, `PATTERN_000364`, `PATTERN_000366` deben congelarse/demotarse hasta tener fills enlazados.
6. **Duplicados y anti-lookahead blanks.** Quedan 125 filas duplicadas repetidas y 271 filas con contrato anti-lookahead en blanco.
7. **Produccion inexistente.** Hay 0 patrones `PRODUCTION`, 0 manifests activos y 0 evidencia productiva.
8. **Exposicion operativa.** `docker-compose.yml` publica `8000:8000` y `3000:3000`; el proxy frontend reenvia peticiones con Basic Auth interno. Si no esta detras de localhost/VPN/firewall, es riesgo preLive.
9. **Paquete reciente requiere inclusion explicita en release.** En el snapshot inicial del 17/06, `research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal/` aparecia sin trackear. Para release debe incluirse completo junto a `file_hashes.sha256`, `manifest.json`, `director_gate_result.*` y las instrucciones de reproduccion.

## 7. Condiciones Para Paper Ampliado

Paper puede seguir si se cumple todo:

- `TRADEO_TRADING_MODE=paper`.
- `TRADEO_LIVE_TRADING_ENABLED=false`.
- `live_armed=false`.
- Kill switch runtime apagado.
- Puerto IBKR paper, no puerto live.
- Entorno solo localhost/VPN/firewall.
- Lab escanea durante mercado abierto.
- Cada order/fill se reconcilia desde IBKR Paper con fill id/hash, broker timestamp, comision, entry variant, regime key y slippage/cost metadata.
- Tras los primeros cierres, se exporta un nuevo audit package y se verifica que `paper_trades.csv` e `ib_fills.csv` ya no estan vacios.

## 8. Condiciones Minimas Para Reconsiderar Live

No recomiendo Live limitado hasta que se cumpla como minimo:

1. Nuevo paquete Director `passed` o sin blockers P0 de metodologia.
2. Al menos 30 fills IBKR Paper normales para el patron candidato.
3. Diversidad minima de simbolos y dias segun `DirectorProductionGate`.
4. `nested_discovery_replay` implementado y pasado, o patron explicitamente capado por debajo de produccion.
5. `event_ledger_hash`, `registry_hash`, `registry_run_manifest_hash` y evidence packet hash presentes.
6. Costes, slippage y fill provenance reconciliados.
7. Regime y entry-variant buckets poblados para el patron.
8. ProductionManifest activo, hash-verificado, aprobado por Director y no expirado.
9. Reconciliacion DB <-> IBKR limpia inmediatamente antes de armar.
10. Aprobacion explicita de Asier para `live_armed`, live mode y sizing inicial muy pequeno.

## 9. Plan De 7 Dias Recomendado

1. **Dia 1:** congelar/demotar los 3 promoted-status offenders; dejar constancia en audit log.
2. **Dia 1-2:** asegurar que backend/frontend solo escuchan en localhost/VPN o poner firewall/reverse proxy autenticado.
3. **Dia 1-3:** ejecutar Lab en horario regular US con `execute_orders=true`; registrar razones si no se envian ordenes.
4. **Dia 2-5:** cerrar el loop IBKR Paper: fills reales, comisiones, hashes, timestamps, slippage.
5. **Dia 3-6:** regenerar audit package con `paper_trades` e `ib_fills` no vacios.
6. **Dia 4-7:** limpiar duplicados, anti-lookahead blanks y nested replay blockers de Research.
7. **Dia 7:** repetir Director gate. Si sigue blocked, no hay conversacion de Live; si pasa para algun patron, preparar manifest, no armar live todavia.

## 10. Conclusion

La direccion es correcta. Tradeo ya se comporta mas como un laboratorio conservador que como un bot impulsivo: los gates bloquean, el dashboard separa evidencia, Fox no puede operar sin manifest, y el sistema evita vender Research como edge demostrado.

Pero para Live falta lo principal: **fills reales de Paper reconciliados y un Director package limpio**. En este momento, lanzar Live seria saltarse precisamente las defensas que se han construido.

Recomendacion final: **Live bloqueado. Paper ampliado y medido.**
