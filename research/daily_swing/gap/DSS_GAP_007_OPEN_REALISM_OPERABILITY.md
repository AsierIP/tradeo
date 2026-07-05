# DSS GAP-007 Open Realism / Operability / Earnings Review

Decision: `OPEN_REALISM_FAIL`.

Open realism:

- Same-day reversal depends on execution at the open after a gap event.
- The required 50 bps adverse open slippage stress is destructive for OBS2 and both MAX_2_NEW_TRADES_PER_DAY target rows.
- OBS1 survives 50 bps under ALL_EVENTS and ONE_ACTIVE_PER_SYMBOL, but that is not enough because the closed confirmatory policy set requires operability under portfolio constraints.

Operability:

- `ONE_ACTIVE_PER_SYMBOL` is not destructive for OBS1 or OBS2.
- `MAX_2_NEW_TRADES_PER_DAY` is destructive for both observations:
  - OBS1 MAX2: expectancy x2 -0.00209933, PF x2 0.878991, 50 bps -0.00509933.
  - OBS2 MAX2: expectancy x2 -0.00211581, PF x2 0.846896, 50 bps -0.00511581.

Earnings / gap extremity:

- Earnings availability is not present as a trusted ledger column, so GAP-007 uses a descriptive extreme-gap proxy only and does not claim an earnings filter.
- The earnings sensitivity row is negative out-of-sample: expectancy x2 -0.00130679, PF x2 0.891347, 50 bps -0.00430679.

Conclusion:

The same-day reversal observations are not robust enough for a clean research survival decision. The terminal blocker is operability under MAX_2_NEW_TRADES_PER_DAY plus open slippage sensitivity.
