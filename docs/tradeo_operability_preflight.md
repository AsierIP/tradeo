# Tradeo Operability Preflight

`scripts/check_tradeo_operability.py` is a read-only local preflight for deciding
whether Tradeo is safe to inspect as an operable, non-trading system.

It does not connect to IBKR, call live endpoints, execute research waves, create
orders, activate paper/live trading, or change gates.

## Usage

```bash
python3 scripts/check_tradeo_operability.py
python3 scripts/check_tradeo_operability.py --json-only
python3 scripts/check_tradeo_operability.py --json-out /tmp/operability.json --md-out /tmp/operability.md
```

By default it writes:

- `artifacts/runtime/operability/latest_operability.json`
- `artifacts/runtime/operability/latest_operability.md`

Optional flags:

- `--repo-root <path>` evaluates a specific checkout.
- `--env-file <path>` reads a specific env file instead of `.env` / `.env.example`.
- `--allow-paper-enabled` permits `TRADEO_INTRADAY_PAPER_ENABLED=true` for an
  explicitly authorized task. There is no option to allow live trading.

## Checks

- Detects repo root, branch, current SHA, dirty status, and summarized tracked /
  untracked changes.
- Runs only `docker compose config --quiet`.
- Verifies critical files for compose, backend, frontend, and intraday research
  scripts.
- Reads `.env` when present, otherwise `.env.example`, and process `TRADEO_*`
  overrides without printing secrets.
- Redacts variables whose names contain `KEY`, `SECRET`, `PASSWORD`, `TOKEN`, or
  `ACCOUNT`, plus values that look like long credentials.
- Reports the latest local universe metadata, readiness manifest, wave manifest,
  forensics output, and planner output if present.

## Statuses

`OPERABLE_READ_ONLY` means the repo is evaluable, critical files are present,
Docker Compose config is valid, env is evaluable, and live/paper/order safety is
fail-closed.

`BLOCKED` means a dangerous or unauthorized flag is active:

- `TRADEO_TRADING_MODE=live`
- `TRADEO_LIVE_TRADING_ENABLED=true`
- `TRADEO_INTRADAY_LIVE_ENABLED=true`
- `TRADEO_IBKR_READONLY=false`
- `TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=true`
- `TRADEO_INTRADAY_PAPER_ENABLED=true` without `--allow-paper-enabled`
- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`
- `TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS=true`
- `TRADEO_IBKR_ALLOW_MARKET_ORDERS=true`
- `TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS=true`
- `TRADEO_INTRADAY_EOD_EMERGENCY_MARKET_ALLOWED=true`
- `TRADEO_ALLOW_OPTIONS=true`
- `TRADEO_ALLOW_MARGIN=true`

`NOT_READY` means no dangerous flag was found, but the preflight could not
complete operability checks because the repo is invalid, a critical file is
missing, Docker Compose config failed, env files are absent, or another
non-dangerous error prevents evaluation.

`TRADEO_KILL_SWITCH_ENABLED=true` is safe and does not block operability; the
preflight reports it as `kill_switch_enabled=true`.

## Limits

This preflight is a control and reporting tool only. It does not:

- connect to IBKR;
- execute research;
- send orders;
- start containers;
- build images;
- call Tradeo endpoints;
- change `.env`;
- change scoring, gates, broker code, or order execution code.

Any `BLOCKED` result should stop the task until Director or Asier resolves the
safety issue.
