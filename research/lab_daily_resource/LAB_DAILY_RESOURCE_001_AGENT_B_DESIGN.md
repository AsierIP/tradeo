# Agent B Design - Daily Setup Watchlist Backend

## Objective

Add a Daily metadata layer between rejected and entry/order so recoverable setups stay visible without becoming orders.

## Files

- `backend/tradeo/modules/daily_swing/setup_watchlist.py`
- `backend/tradeo/routers/daily.py`
- Daily watchlist tests.

## Contracts

- Input: source match snapshot and `SetupEvaluation`.
- Output: `DailySetup`, stable evidence hash, watchlist artifact, optional Lab Paper Probe request metadata with `submits_order=false`.

## Risks

- Entry-ready being interpreted as order permission.
- Structural failures entering the watchlist.
- Daily metrics blending with Intraday/Lab/FoxHunter.

## Tests

- Recoverable reasons enter.
- Non-recoverable reasons and low reward/risk do not enter.
- Entry-ready does not submit orders.
- Direct entered transition is blocked unless already entry-ready.
- max_active and stable hash.

## Fail-Safe

Artifacts and setup records carry `orders_allowed=false`, `paper_allowed=false`, `live_allowed=false`, `submit_order_called=false`.
