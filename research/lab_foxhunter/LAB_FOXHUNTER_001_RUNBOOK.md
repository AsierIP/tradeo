# LAB_FOXHUNTER_001 Runbook

1. Validate proposed probe manifests with `scripts/check_lab_foxhunter_gate.py`.
2. Keep every probe disabled by default until a later authorized paper-only batch.
3. During Lab paper operation, record every event with the telemetry fields in this folder's initial probe document.
4. At the 20-trade milestone, evaluate Lab -> FoxHunter metrics.
5. If eligible, open FoxHunter review; do not promote to live automatically.

Safety invariants: no live, no paper orders in this task, no previews, no operational signals, no IBKR operational use, no downloads, no cron trading, no `.env` edits.
