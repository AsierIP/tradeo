# Intraday Runbooks

Date: 2026-06-22

## Session Start

- Confirm `TRADEO_INTRADAY_ENABLED=false` unless deliberately running shadow.
- Check `/health/config-doctor`.
- Confirm calendar availability and today's cutoffs.
- Confirm pacing budget has spare capacity before data sync.
- Confirm previous session flat status is `FLAT_CONFIRMED`.

## IBKR Failure

- Stop new entries immediately.
- Keep reduce-only exits available if broker snapshots are trustworthy.
- If broker is unreachable near flat deadline, mark `FLAT_FAILED` and require manual intervention.
- Do not infer flat from DB alone.

## Pacing Exhausted

- Degrade scanner to shadow/stale-safe.
- Skip new entry candidates.
- Keep open-position refresh and flat/reconcile ahead of new discovery.

## Non-Liquid Position

- Cancel unfilled entry orders first.
- Use reduce-only limit/marketable-limit exits.
- If halted/rejected/illiquid past deadline, set kill switch and record unresolved exposure.

## Half Day

- Use `IntradayMarketCalendar` cutoffs, not server-local fixed times.
- Verify no-new-entry, cancel-entry and flat windows are pulled forward.

## Kill Switch

- Trigger on flat failure, broker/DB desync, stale data, unknown calendar or max loss.
- New entries stay blocked.
- Reduce-only can continue when it reduces real broker exposure.

## Post-Session Audit

- Export intraday session report.
- Verify candidates, trades, EV realized vs expected, pacing, risk ledger and flat compliance.
- Keep shadow, paper and live records labeled separately.
