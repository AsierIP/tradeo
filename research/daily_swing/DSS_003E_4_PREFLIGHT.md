# DSS-003E-4 Preflight

Generated at: 2026-07-04T15:03:50Z

Decision: PREFLIGHT_PASS

- 127.0.0.1:4002: TCP_OK.
- host.docker.internal:4002 from Docker: TCP_OK.
- Port classification: IB_GATEWAY_PAPER.
- read_only=true.
- Live ports 4001 and 7496: blocked by diagnostic guard as LIVE_PORT_RISK.
- Initial SPY 5D canary: OK, bars_count=5.
- Initial AAON 5D canary: OK, bars_count=5.

No account data, orders, paper orders, live orders, batch cache, backtest, signals, preview, cron, gh, merge, or .env modifications were used in preflight.
