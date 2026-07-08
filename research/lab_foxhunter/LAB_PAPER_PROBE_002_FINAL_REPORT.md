# T-LAB-PAPER-PROBE-002 Final Report

## A. Resumen ejecutivo

Decisión final: `LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED`.

Se preparó el batch supervisado `LAB_PAPER_PROBE_ONLY` para `LAB-GAP-REV-001` y `LAB-GAP-REV-002`, pero no se enviaron órdenes paper. El runner bloqueó correctamente porque el estado seguro final mantiene `TRADEO_IBKR_READONLY=true`; para enviar paper habría que abrir escritura, y esta sesión no tiene verificación inequívoca suficiente para hacerlo sin elevar riesgo.

Antes del bloqueo final se corrigió una deriva insegura del `.env` real: estaba con `TRADEO_IBKR_READONLY=false` y `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`. Se creó backup no versionado y se endureció a readonly true + auto-submit general false.

## B. Path real usado

- framework worktree: `/tmp/tradeo-lab-foxhunter-001`
- repo base con `.env` real: `/home/vboxuser/tradeo`
- backup `.env`: `/home/vboxuser/tradeo/.env.lab_paper_probe_backup_20260706_0749`

## C. Rama/commit/push

- branch: `feature/lab-foxhunter-gate-001`
- HEAD: `f0d2cc284548647ea1d2dcd807f842e9cf14a436`
- remote sync: `git fetch origin` + `git pull --ff-only origin feature/lab-foxhunter-gate-001` -> up to date
- push: `origin/feature/lab-foxhunter-gate-001`

## D. Pre-market safety gate

- `PAPER_INFRA_READY`: `READY_FOR_DIRECTOR_PAPER_REVIEW`
- live trading: blocked
- intraday live: disabled
- intraday paper general: disabled
- market orders: disabled
- general lab auto-submit: disabled
- IBKR readonly: enabled
- paper orders sent: `0`
- live orders sent: `0`

Artifact: `research/lab_foxhunter/LAB_PAPER_PROBE_002_PREMARKET_SAFETY.md` and `.json`.

## E. Probe manifest gate

- `LAB-GAP-REV-001`: enabled only as `lab_paper_probe`
- `LAB-GAP-REV-002`: enabled only as `lab_paper_probe`
- `foxhunter_candidate=false`
- `live_candidate=false`
- `paper_candidate=false`
- `generate_signals=false`
- `generate_previews=false`
- `live_allowed=false`

Artifact: `research/lab_foxhunter/LAB_PAPER_PROBE_002_MANIFEST_GATE.md`.

## F. IBKR paper-only gate

Status: `BLOCKED_READONLY_WRITE_REQUIRED`.

The environment is now safe for review but not open for paper write. Paper mode/port class are non-live, but no sensitive account id was logged and no submit path was opened.

Artifact: `research/lab_foxhunter/LAB_PAPER_PROBE_002_IBKR_PAPER_GATE.md` and `.json`.

## G. Runner dry-run

Command used:

```bash
python3 scripts/run_lab_paper_probe_batch.py --lab-paper-probe --probe-manifest research/lab_foxhunter/probes/LAB-GAP-REV-001.json --probe-manifest research/lab_foxhunter/probes/LAB-GAP-REV-002.json --paper-only --no-live --max-orders-total 2 --env-file /home/vboxuser/tradeo/.env --runtime-out artifacts/runtime/lab_paper_probe/lab_paper_probe_2026-07-06.json --dry-run
```

Result: `LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED`.

## H. Paper orders executed

None.

## I. No-trade reasons

- `BLOCKED_READONLY_WRITE_REQUIRED`
- No market/open trigger evaluation proceeded after the safety block.

## J. Telemetry/fills/slippage

Runtime artifact: `artifacts/runtime/lab_paper_probe/lab_paper_probe_2026-07-06.json`.

- orders: `[]`
- fills: none
- slippage: none
- latency: none

## K. Tests/validaciones

- `py_compile`: pass
- focal pytest in Docker: `29 passed`
- ruff touched files in Docker: pass
- `git diff --check`: pass
- JSON validation: pass
- tracked-path security scan: pass; no `.env`, `artifacts/runtime`, `MEMORY.md`, `memory/`, logs, or caches tracked

## L. Decisión final

`LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED`.

## M. Confirmaciones

- no live: confirmed
- no real orders: confirmed
- no paper orders: confirmed
- no FoxHunter promotion: confirmed
- no `live_candidate`: confirmed
- no classic `paper_candidate`: confirmed
- no `gh`: confirmed
- no main push: confirmed
- no merge: confirmed
- no scoring changes: confirmed
- no Research gate relaxation: confirmed

## N. Siguiente acción

Post-market or next supervised window: only consider paper submit if an explicit paper-write overlay is designed and verified with paper account identity, kill-switch behavior, isolated runner path, no general auto-submit, and redacted audit logging. Until then, stay in readonly Lab Paper Probe readiness only.
