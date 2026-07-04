# DSS-003E-3 API Session Handshake

Task: T-DAILY-SWING-003E-3

Decision: API_HANDSHAKE_PASS

## Scope

This probe separated raw TCP reachability from IB API handshake readiness. It did not request account data, orders, paper orders, live orders, signals, previews, backtests, or research-150 cache batches.

## Result

- Host TCP 127.0.0.1:4002: TCP_OK.
- Docker TCP host.docker.internal:4002: TCP_OK.
- Port classification: IB_GATEWAY_PAPER.
- Client id 17: connected=true, serverVersion=176.
- Client id 117: connected=true, serverVersion=176.
- Client id 217: connected=true, serverVersion=176.
- Live diagnostic ports 4001 and 7496: blocked by guard, not contacted through IB API.

## Artifact

- `artifacts/runtime/daily_swing/dss_003e_3_api_session.json`
- `artifacts/runtime/daily_swing/dss_003e_3_tcp_host.json`
- `artifacts/runtime/daily_swing/dss_003e_3_tcp_docker.json`
- `artifacts/runtime/daily_swing/dss_003e_3_live_port_4001.json`
- `artifacts/runtime/daily_swing/dss_003e_3_live_port_7496.json`
