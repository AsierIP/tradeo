# DSS-003E-2 Preflight

Decision: BLOCKED_CANARY

## Checks

- Host TCP `127.0.0.1:4002`: TCP_OK.
- Docker TCP `host.docker.internal:4002`: TCP_OK.
- Port classification: IB_GATEWAY_PAPER.
- Read-only probe settings: `read_only=true`, port `4002`.
- Live ports `4001` and `7496`: blocked by diagnostic guard as LIVE_PORT_RISK, not used.

## Historical canary

- SPY 5D Daily: FAILED, `historical_data_ok=false`, connected=false, TimeoutError from API connection.
- AAON 5D Daily: FAILED, `historical_data_ok=false`, connected=false, TimeoutError from API connection.

## Decision

Preflight does not allow a cache run. TCP is reachable, but the IBKR API historical canary failed for both benchmark/regime and operational symbols. Per DSS-003E-2 safety rule, stop before any batch download.

Safety: no orders, no paper orders, no live orders, no paper execution, no backtest, no signals, no preview, no cron, no `.env` real modification.
