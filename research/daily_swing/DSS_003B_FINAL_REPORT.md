# DSS-003B Final Report

Generated: 2026-07-04 09:41 UTC.

## Executive Summary

DSS-003B narrowed the blocker to local IBKR/TWS/Gateway connectivity. The repo configuration is read-only and targets safe TWS paper port `7497`, but `host.docker.internal` does not resolve from the host execution context and `127.0.0.1:7497` refuses TCP. No historical probe, smoke cache, pilot cache, backtest, paper trading, live trading, signals, orders, cron, or real `.env` changes were performed.

## Branch

- Branch: `feature/daily-swing-paper-probe-001`.
- Base before DSS-003B: `c67f0bd feat(daily): add DSS-003 daily cache gate`.

## Config Effective

- Host: `host.docker.internal`.
- Port: `7497`.
- Client ID: `17`.
- Read-only: `true`.
- Port classification: TWS paper.

## DNS And TCP

- `host.docker.internal:7497`: `DNS_FAIL`.
- `127.0.0.1:7497`: `TCP_REFUSED`.
- `host.docker.internal:4002`: `DNS_FAIL`.
- Temporary Docker `--add-host=host.docker.internal:host-gateway`: DNS resolves to Docker host gateway.

## Artifacts

- `scripts/diagnose_ibkr_connectivity.py`.
- `scripts/probe_ibkr_historical_readonly.py`.
- `docker-compose.ibkr-local.override.example.yml`.
- `artifacts/runtime/daily_swing/dss_003b_tcp_probe.json`.
- `artifacts/runtime/daily_swing/dss_003b_decision.json`.
- `research/daily_swing/DSS_003B_EFFECTIVE_CONFIG.md`.
- `research/daily_swing/DSS_003B_DOCKER_HOST_RESOLUTION.md`.
- `research/daily_swing/DSS_003B_TCP_PROBE.md`.
- `research/daily_swing/DSS_003B_HISTORICAL_PROBE.md`.

## Validation

- `python3 -m py_compile scripts/diagnose_ibkr_connectivity.py scripts/probe_ibkr_historical_readonly.py scripts/cache_daily_ohlcv.py scripts/check_daily_ohlcv_quality.py`: exit 0.
- `pytest -q backend/tradeo/tests/test_daily_swing_dss_003b.py backend/tradeo/tests/test_daily_swing_dss_003.py`: 15 passed, exit 0.
- `ruff check scripts/diagnose_ibkr_connectivity.py scripts/probe_ibkr_historical_readonly.py backend/tradeo/tests/test_daily_swing_dss_003b.py`: exit 0.
- `git diff --check`: exit 0.
- `docker compose --env-file .env.example build backend`: exit 0.

## Decision

`BLOCKED_NEEDS_ASIER_LOCAL_ACTION`.

## Minimal Asier Action

1. Open TWS paper or IB Gateway paper.
2. Enable API socket clients.
3. Confirm the listening paper port:
   - TWS paper: `7497`.
   - IB Gateway paper: `4002`.
4. If running from host, test with:

```bash
python3 scripts/diagnose_ibkr_connectivity.py --host 127.0.0.1 --port 7497
```

5. If running inside Docker, keep `host.docker.internal:host-gateway` and test from the backend container once `.env` is available.

Only after a safe paper endpoint returns `TCP_OK` should DSS-003B run the historical read-only probe and then the DSS-003 smoke cache.
