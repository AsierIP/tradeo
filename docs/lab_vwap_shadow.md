# Lab VWAP Shadow

T-LAB-001 adds a read-only VWAP shadow recorder for real-time Lab evidence.
It records theoretical opportunities and microstructure fields without sending
orders.

## Scope

- No broker submit path.
- No IBKR order placement.
- No Paper orders.
- No Live orders.
- No production gate or scoring changes.
- Smoke output is JSON/Markdown under `artifacts/runtime/lab_shadow/`.

## Smoke

```bash
python3 scripts/run_vwap_shadow_once.py \
  --symbol AAPL \
  --side long \
  --vwap-condition vwap_reclaim_long \
  --timeframe 1m \
  --json-out artifacts/runtime/lab_shadow/latest_shadow.json \
  --md-out artifacts/runtime/lab_shadow/latest_shadow.md
```

Acceptable smoke decisions:

- `shadow_recorded`
- `market_closed`
- `quote_unavailable`
- `blocked_safety`

Forbidden outcomes:

- `order_submitted`
- `paper_order_submitted`
- `live_order_submitted`

## Recorded Fields

The schema is `tradeo.lab_vwap_shadow.v1` and includes symbol, side,
timeframe, VWAP condition, VWAP entry/exit context, theoretical entry/stop/target,
bid/ask/last, spread, latency, MFE/MAE, gross/net R estimates, cost x2 estimate,
decision reason, IBKR status, and explicit false safety flags.

## T-LAB-002 Readiness

T-LAB-002 should only be authorized after Shadow records are stable:

- Shadow writes JSON/Markdown artifacts consistently.
- No safety errors or broker/order calls appear.
- Quotes are available or unavailable with explicit reason.
- Spread and latency are present when quotes are available.
- MFE/MAE update path is demonstrated with future bars or observation closer.
- `orders_allowed=false`, `paper_allowed=false`, and `live_allowed=false` remain true for every record.
