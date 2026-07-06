# LAB_FOXHUNTER_001 Runbook

This runbook prepares the Lab to FoxHunter promotion framework only. Do not submit paper orders, live orders, order previews, or operational signals during this task.

## Validate Framework

From repo root:

```bash
python -m py_compile scripts/check_lab_foxhunter_gate.py backend/tradeo/modules/lab_foxhunter/gates.py
python scripts/check_lab_foxhunter_gate.py --research-root research/lab_foxhunter
pytest backend/tradeo/tests/test_lab_foxhunter_gates.py
pytest backend/tradeo/tests/test_intraday_paper_execution.py backend/tradeo/tests/test_prepaper_release_readiness.py
git diff --check
```

Run `ruff` on touched files when available:

```bash
ruff check scripts/check_lab_foxhunter_gate.py backend/tradeo/modules/lab_foxhunter/gates.py backend/tradeo/tests/test_lab_foxhunter_gates.py
```

## Future Paper Probe Phase

Paper execution may only be considered in a later task, expected as:

`T-LAB-PAPER-PROBE-002 - Enable first supervised paper probe batch, paper-only, max 2 probes, no FoxHunter promotion.`

Before any future paper order:

- Probe must be a valid `lab_paper_probe`.
- Probe must remain isolated from live.
- A paper-probe mode must be explicit.
- Global auto-submit must not be used as a shortcut.
- `IBKR_READONLY=true` and `LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false` safety posture must be reviewed, not bypassed.
- Direccion must authorize the supervised batch.

## Prohibited During This Task

- Live orders.
- Paper orders.
- Simulated broker orders.
- Order previews.
- Operational signals.
- Cron trading.
- `.env` changes.
- Data downloads.
- IBKR operational use.
- Creating real FoxHunter candidates.
- Creating live candidates.
