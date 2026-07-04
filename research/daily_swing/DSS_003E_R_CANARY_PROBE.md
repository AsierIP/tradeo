# DSS-003E-R Canary Probe

Decision: HISTORICAL_FARM_OK

TCP preflight:
- `127.0.0.1:4002`: TCP_OK, IB_GATEWAY_PAPER.
- Docker `host.docker.internal:4002`: TCP_OK, IB_GATEWAY_PAPER.
- Live ports were not used.

Historical read-only probes:

| Symbol | Period | Status | Bars |
| --- | --- | --- | ---: |
| SPY | 5D | OK | 5 |
| SPY | 1M | OK | 501 |
| AAON | 5D | OK | 5 |
| AAON | 1M | OK | 501 |
| AAON | 3Y | OK | 752 |
| AAPL | 3Y | OK | 752 |

Interpretation: the historical farm is reachable now. The previous AAON timeout was not reproduced by canary and is best treated as transient API/session instability plus insufficient loader resilience.

Safety: read-only only; no orders, no paper orders, no live.
