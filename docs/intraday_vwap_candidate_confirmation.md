# Intraday VWAP Candidate Confirmation

Read-only tooling for T-RESEARCH-VWAP-007 confirms whether a single exact-scope
VWAP candidate can justify a later narrow confirmation wave.

## Scope

- Candidate: `run_id=6454`, `pattern_key=novel_long_w100_551e1329b8e371f19e35`.
- No waves, Shadow, paper, live, orders, IBKR, or DB writes.
- The analyzer prefers the exact-scope event ledger gzip when present, and uses
  existing forensics/evidence artifacts plus OHLCV cache files for reconstruction.
- Missing fields remain `null`; the analyzer does not invent events.

## Overlays

The CLI evaluates fixed overlays only:

- `baseline_existing`
- `exit_on_vwap_loss`
- `exit_on_failed_reclaim` with `N=2`
- `exit_on_close_below_vwap_after_entry`
- `exit_on_vwap_loss_or_time_stop`
- `exit_on_vwap_loss_or_4R_takeprofit`

No threshold grid search is performed.

## Decision

`confirm_candidate_ready_for_narrow_wave` requires a predefined overlay with
drawdown `<= 12R`, positive expectancy, profit factor `> 1.2`, enough events,
at least six symbols, and no extreme symbol/month concentration.

If exported/DB/cache data cannot reconstruct enough candidate events, the output
is `insufficient_event_data`.
