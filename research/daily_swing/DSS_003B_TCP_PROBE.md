# DSS-003B TCP Probe

Generated: 2026-07-04 09:41 UTC.

## Results

| Endpoint | Port class | DNS | TCP | Decision |
| --- | --- | --- | --- | --- |
| `host.docker.internal:7497` | TWS paper | `DNS_FAIL` | not run | `DNS_FAIL` |
| `127.0.0.1:7497` | TWS paper | `DNS_OK` | `TCP_REFUSED` | `TCP_REFUSED` |
| `host.docker.internal:4002` | IB Gateway paper | `DNS_FAIL` | not run | `DNS_FAIL` |

## Artifact

- `artifacts/runtime/daily_swing/dss_003b_tcp_probe.json`
- Additional local probes:
  - `artifacts/runtime/daily_swing/dss_003b_tcp_probe_127001_7497.json`
  - `artifacts/runtime/daily_swing/dss_003b_tcp_probe_hostdocker_4002.json`

## Interpretation

Host-level `host.docker.internal` DNS is missing. The direct host socket `127.0.0.1:7497` resolves but refuses TCP, which is consistent with TWS/Gateway not listening on that host port, the API socket being disabled, or a different configured IBKR port.
