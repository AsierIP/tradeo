# T-LAB-PAPER-PROBE-005 Final Report

## A. Resumen ejecutivo

Decision final: `LAB_PAPER_PROBE_BLOCKED_SPREAD_OR_MARKET_DATA`.
Se revalidaron los gates Lab Paper Probe; no se enviaron ordenes porque la ejecucion ocurrio fuera de la sesion regular USA.

## B. Path real usado

- framework worktree: `/tmp/tradeo-lab-foxhunter-001`
- repo base con `.env` real: `/home/vboxuser/tradeo/.env`
- overlay temporal: `/tmp/tradeo_lab_paper_write_overlay_20260706_probe005.env`
- overlay eliminado al terminar: `True`

## C. Rama/commit/push

- branch: `feature/lab-foxhunter-gate-001`
- commit/push: pendiente hasta validacion final de esta tarea; no se toca main ni se usa gh.

## D. Safety/account gate

- status: `PASS`
- blockers: `[]`

## E. Trigger/manifest gate

- status: `PASS`
- probes: `['LAB-GAP-REV-001', 'LAB-GAP-REV-002']`
- blockers: `[]`

## F. Execution result

- decision: `LAB_PAPER_PROBE_BLOCKED_SPREAD_OR_MARKET_DATA`
- no_trade_reason: `NO_TRADE_SPREAD_OR_MARKET_DATA`
- market_data_gate: `NO_TRADE_SPREAD_OR_MARKET_DATA`

## G. Paper orders executed

`0`

## H. No-trade reasons

`NO_TRADE_SPREAD_OR_MARKET_DATA`; blockers `['outside_regular_us_session']`.

## I. Reconciliation/fills/slippage/latency

- reconciliation: `RECONCILIATION_NO_ORDERS`
- fills: `[]`
- slippage_bps: `None`
- latency_ms: `None`

## J. Tests/validaciones

- py_compile runner/gates: PASS
- pytest focal lab_foxhunter + paper_readiness: PASS
- ruff touched files: PASS
- git diff --check: PASS
- JSON validation: PASS
- security scan: PASS, no .env/overlay/runtime/memory tracked and no raw account id/token/password/private key in tracked artifacts

## K. Decision final

`LAB_PAPER_PROBE_BLOCKED_SPREAD_OR_MARKET_DATA`

## L. Confirmaciones

- no live: confirmed
- no real orders: confirmed
- no FoxHunter promotion: confirmed
- no live_candidate: confirmed
- no classic paper_candidate: confirmed
- no gh: confirmed
- no main push: confirmed

## M. Siguiente accion

Reintentar T-LAB-PAPER-PROBE-005 durante sesion regular USA si Direccion mantiene la autorizacion y los gates siguen PASS.
