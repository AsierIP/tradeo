# DSS-003B Effective Config

Generated: 2026-07-04 09:41 UTC.

## Scope

This inspection covers only IBKR read-only connectivity for Daily DSS-003B. No orders, paper orders, live trading, signal generation, cron activation, or real `.env` modification were performed.

## Effective Settings

- Source: `tradeo.core.config.Settings` defaults and `.env.example`.
- Host: `host.docker.internal`.
- Port: `7497`.
- Client ID: `17`.
- Read-only: `true`.
- Connect timeout: `8.0` seconds.
- Account: not reported; secrets/accounts are intentionally excluded.

## Port Classification

- `7497`: TWS paper port, allowed for read-only diagnostics.
- `4002`: IB Gateway paper port, allowed for read-only diagnostics.
- `7496` and `4001`: live-port risk, blocked by DSS-003B diagnostic script.

## Findings

The effective host/port path remains `host.docker.internal:7497`. The setting is read-only and not a live IBKR port. The current blocker is name resolution for `host.docker.internal` in the host execution context, not a strategy or order-path issue.
