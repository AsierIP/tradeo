# T-LAB-DAILY-RESOURCE-002 Watchlist Hardening

- status: `PASS`
- module: `backend/tradeo/modules/daily_swing/setup_watchlist.py`

## Confirmed

- `entry_ready` creates only `lab_paper_probe_request` metadata.
- `lab_paper_probe_request.submits_order=false`.
- `orders_allowed=false`, `paper_allowed=false`, `live_allowed=false`.
- Non-recoverable reasons do not enter the watchlist.
- Recoverable reasons enter the watchlist when reward/risk is acceptable.
- `max_age_days` expiration and invalidation paths are covered by tests.
- Daily payload uses timeframe `1d` and does not mix Lab/FoxHunter metrics.

## Decision

`WATCHLIST_ORDERLESS_METADATA_ONLY`
