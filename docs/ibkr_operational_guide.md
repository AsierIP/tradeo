# Tradeo IBKR operational guide

This integration is designed for controlled IBKR paper/live execution through TWS or IB Gateway.

## Default posture

Keep the first phase read-only:

```bash
TRADEO_TRADING_MODE=paper
TRADEO_IBKR_HOST=host.docker.internal
TRADEO_IBKR_PORT=7497
TRADEO_IBKR_CLIENT_ID=17
TRADEO_IBKR_READONLY=true
TRADEO_LIVE_TRADING_ENABLED=false
TRADEO_LIVE_TRADING_CONFIRMATION_VALUE=
TRADEO_KILL_SWITCH_ENABLED=false
```

## Endpoints

All endpoints are under `/api`:

```text
GET  /api/ibkr/health
GET  /api/ibkr/account
GET  /api/ibkr/positions
GET  /api/ibkr/open-orders
POST /api/ibkr/signals/{signal_id}/preview
POST /api/ibkr/signals/{signal_id}/submit-bracket
```

The submit endpoint is blocked unless all hard gates pass:

- `TRADEO_IBKR_READONLY=false`;
- kill switch is off;
- signal has `human_approved=true`;
- signal status is `paper_approved` or `live_approved`;
- order notional is below `TRADEO_IBKR_MAX_ORDER_VALUE_USD`;
- live ports or live mode require `live_armed=true`.

## Suggested setup steps

1. Start TWS or IB Gateway in paper mode.
2. Enable API socket clients in TWS/Gateway.
3. Verify the socket port.
4. Run:

```bash
curl http://localhost:8000/api/ibkr/health
```

5. Keep orders blocked until health/account/positions are stable.
6. For IBKR paper order testing only, set:

```bash
TRADEO_IBKR_READONLY=false
TRADEO_TRADING_MODE=paper
TRADEO_IBKR_PORT=7497
```

7. Never point to live ports (`7496` or `4001`) unless the live gate is deliberately armed.

## Live mode gate

Live execution requires all of this:

```bash
TRADEO_TRADING_MODE=live
TRADEO_LIVE_TRADING_ENABLED=true
TRADEO_LIVE_TRADING_CONFIRMATION_VALUE=I_ACCEPT_LIVE_MARKET_RISK
TRADEO_IBKR_READONLY=false
TRADEO_KILL_SWITCH_ENABLED=false
```

This still does not bypass human approval on the signal.
