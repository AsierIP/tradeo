# LAB Paper Probe 002 Runbook

This runbook prepares the first supervised Lab paper-probe batch. It does not submit broker orders and does not generate operational signals or order previews.

## Preflight

From repo root:

```bash
python scripts/prepare_lab_paper_probe_batch.py \
  --paper-probe-mode \
  --director-approved \
  --json-out artifacts/runtime/lab_foxhunter/lab_paper_probe_002_batch.json \
  --md-out artifacts/runtime/lab_foxhunter/lab_paper_probe_002_batch.md
```

The runtime outputs above are local artifacts and must not be committed.

## Required Safe State

- Explicit paper-probe mode is enabled for this batch only.
- Director approval is present.
- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false`.
- `TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS=false`.
- Live trading disabled.
- `live_armed=false`.
- Kill-switch available.
- Risk limits available.
- No cron trading path.
- No signal generation.
- No order preview generation.
- No broker submit from this batch-preparation task.

## Stop Immediately If

- More than two probes are selected.
- A non-GAP probe appears.
- PB/BO/CO/CW appears.
- Any task output contains paper/live order IDs.
- Any task output contains order preview IDs.
- Any task output contains operational signals.
- Any FoxHunter/live candidate is created.
- Global auto-submit is enabled.
- Live is enabled or armed.

## Next Runtime Phase

A later supervised runtime task may wire the batch to broker paper execution only after a fresh preflight proves the explicit paper-probe path is safe. This task intentionally leaves broker submission disabled.
