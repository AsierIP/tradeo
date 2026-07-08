# LAB_PAPER_PROBE_002 IBKR Paper Gate

- status: `BLOCKED_READONLY_WRITE_REQUIRED`
- trading mode: `paper`
- IBKR port class: `paper/non-live`
- live armed: `false`
- live trading enabled: `false`
- intraday live enabled: `false`
- general lab auto-submit: `false`
- IBKR readonly: `true`
- paper account verified without sensitive account logging: `mode/port verified only`
- account ids/tokens/secrets logged: `false`
- paper orders sent: `0`
- live orders sent: `0`

The preflight found an unsafe initial `.env` drift:

- `TRADEO_IBKR_READONLY=false`
- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`

A non-versioned backup was created at `/home/vboxuser/tradeo/.env.lab_paper_probe_backup_20260706_0749`, then the real `.env` was hardened to:

- `TRADEO_IBKR_READONLY=true`
- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false`

No submit path was opened. Because paper submit would require disabling readonly, the batch is blocked under `LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED`.
