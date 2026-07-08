# T-LAB-PAPER-PROBE-005 Ramp Final Report

## A. Resumen ejecutivo

Decision final: `LAB_PAPER_PROBE_BLOCKED_SPREAD_OR_MARKET_DATA`.

Se acepto el cambio director de que paper se use como muestreo Lab amplio, pero esta ejecucion no podia abrir smoke ni ramp porque ocurrio fuera de la sesion regular USA. No se enviaron ordenes paper ni live.

## B. Path real usado

- framework worktree: `/tmp/tradeo-lab-foxhunter-001`
- repo base con `.env` real: `/home/vboxuser/tradeo/.env`
- runtime no versionado base: `artifacts/runtime/lab_paper_probe/lab_paper_probe_2026-07-06_probe005.json`
- ramp runtime solicitado: no creado con ordenes porque la ejecucion quedo bloqueada antes de submit

## C. Rama/commit/push

- branch: `feature/lab-foxhunter-gate-001`
- base commit previo: `002d2b8 feat(lab): add paper probe 005 session gate`
- push final de este artifact: pendiente hasta validacion final
- main: no tocado
- gh: no usado

## D. Smoke operativo

- safety/account gate: `PASS`
- trigger/manifest gate: `PASS`
- market/session gate: `BLOCKED`
- reason: `outside_regular_us_session`
- checked_at_new_york: `2026-07-06T05:03:42-04:00`
- regular_session: `09:30-16:00 America/New_York`

## E. Condiciones para ramp

Ramp no iniciado. La condicion minima de sesion regular USA no paso. No se evaluo NBBO, spread, trigger ni submit.

## F. Ramp execution

No aplica. `orders_attempted=0`, `orders_submitted=0`, `orders_filled=0`.

## G. Paper orders/fills redaccionados

No hubo ordenes ni fills. Cuenta permanece redaccionada en artifacts 005 por hash/suffix.

## H. Reconciliation

`RECONCILIATION_NO_ORDERS`. No live orders, no extra orders, no fills, no open-position changes atribuibles a esta tarea.

## I. Slippage/spread/latency

Sin datos: no hubo submit ni market data valida dentro de ventana regular.

## J. Progreso hacia 20 trades por probe

- `LAB-GAP-REV-001`: `0/20`
- `LAB-GAP-REV-002`: `0/20`
- gate_to_foxhunter_status: `NOT_ELIGIBLE_UNDER_20_TRADES`

## K. Tests/validaciones

- py_compile runner/gates: PASS
- pytest focal lab_foxhunter + paper_readiness: PASS, `45 passed`
- ruff touched files: PASS
- git diff --check: PASS
- JSON validation: PASS
- security scan: PASS, no `.env`, overlay, runtime, memory, raw account id, token, password or private key tracked

## L. Decision final

`LAB_PAPER_PROBE_BLOCKED_SPREAD_OR_MARKET_DATA`

## M. Confirmaciones

- no live: confirmed
- no real orders: confirmed
- no FoxHunter promotion: confirmed
- no live_candidate: confirmed
- no classic paper_candidate: confirmed
- no gh: confirmed
- no main push: confirmed

## N. Siguiente accion

Reintentar smoke/ramp durante sesion regular USA si Direccion mantiene la autorizacion. Mantener anti-live, anti-loop, redaccion y reconciliacion; retirar el limite fijo de 2 papers solo dentro de un runner ramp con gates de sesion, cuenta, kill-switch, spread, allowlist y auditoria.
