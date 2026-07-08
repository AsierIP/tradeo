# T-LAB-PAPER-PROBE-003 Final Report

## A. Resumen ejecutivo

Decision final: `LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT`.

Se creo y valido un overlay temporal de escritura paper, pero no se envio ninguna orden paper. La ejecucion quedo bloqueada antes del canary porque no pudo verificarse una cuenta paper IBKR de forma inequivoca desde este entorno.

## B. Path real usado

- framework worktree: `/tmp/tradeo-lab-foxhunter-001`
- repo base con `.env` real: `/home/vboxuser/tradeo/.env`
- overlay temporal: `/tmp/tradeo_lab_paper_write_overlay_20260706.env`
- overlay eliminado al terminar: `True`

## C. Rama/commit/push

- branch: `feature/lab-foxhunter-gate-001`
- implementation commit: `78a1dcb feat(lab): add paper overlay canary gate`
- push: `origin/feature/lab-foxhunter-gate-001`
- main: not touched
- gh: not used

## D. Env overlay gate

- status: `PASS`
- overlay_tracked: `False`
- overlay_keys: `['TRADEO_IBKR_READONLY', 'TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS', 'TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED', 'TRADEO_LIVE_ARMED']`

## E. Paper account gate

- status: `BLOCKED`
- port_class: `paper_proxy`
- connected: `True`
- blockers: `['configured_account_not_managed']`
- error: `None`

## F. Canary result

- decision: `CANARY_BLOCKED_PAPER_ACCOUNT`
- status: `SKIPPED`
- orders: `0`

## G. Probe runner result

- decision: `LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER`
- orders: `0`
- warnings: `['submit_adapter_not_connected']`

## H. Paper orders executed

None.

## I. No-trade reasons

- `LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT`
- blockers: `['paper_account:BLOCKED', 'paper_account:configured_account_not_managed', 'canary:SKIPPED', 'canary:paper_account_gate_not_pass']`

## J. Telemetry/fills/slippage

- fills: none
- slippage: none
- latency: none
- accounts: redacted; no raw account id logged

## K. Tests/validaciones

- py_compile runner/gates: PASS
- pytest focal lab_foxhunter + paper_readiness: PASS, 35 passed
- ruff touched files: PASS
- git diff --check: PASS
- JSON validation: PASS
- security scan: PASS, no .env/overlay/runtime/memory tracked and no raw account id in tracked artifacts

## L. Decision final

`LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT`

## M. Confirmaciones

- no live: confirmed
- no real orders: confirmed
- no paper orders: confirmed
- no FoxHunter promotion: confirmed
- no live_candidate: confirmed
- no classic paper_candidate: confirmed
- no gh: confirmed
- no main push: confirmed

## N. Siguiente accion

Corregir la cuenta configurada o la sesion IBKR paper para que la cuenta gestionada sea inequivocamente paper DU; despues repetir solo paper account gate y canary. Hasta entonces no ejecutar probes.
