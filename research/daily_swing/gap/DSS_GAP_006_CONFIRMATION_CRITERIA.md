# DSS GAP-006 Confirmation Criteria

Generated: 2026-07-05T16:30:00Z

## Future GAP-007 Pass Scope

GAP-007 may only return `CONFIRMATION_SURVIVES_RESEARCH`. It may not return paper, shadow, live, signal, preview, or order approval.

Minimum survival requirements:

- OOS x2 expectancy > 0.
- OOS PF x2 >= 1.2.
- OOS PF x3 >= 1.1 preferred.
- Open slippage 25 bps remains non-destructive.
- Open slippage 50 bps does not become negative.
- `ONE_ACTIVE_PER_SYMBOL` does not destroy the observation.
- `MAX_2_NEW_TRADES_PER_DAY` does not destroy the observation.
- OOS symbols >= 20 and OOS event count remains adequate.
- Top 3 symbols and top 5 events do not explain most of the effect.
- Last 12 months is not negative.
- Matched non-gap, sign-inverted, delayed-entry, and random matched controls do not dominate.
- FDR/WRC/SPA-light does not fail materially.
- No lookahead or open-realism failure.

Hard rejection rules:

- PF x2 < 1.0.
- x2 expectancy <= 0.
- Open slippage 25 bps destroys the effect.
- Open slippage 50 bps remains negative.
- Operable policies destroy the effect.
- Baseline or placebo dominates.
- Effect is concentrated in a few symbols or events.
- Last 12 months is negative.
- Earnings unknown dominates and cannot be controlled.
- FDR/WRC/SPA-light fails.
- Effective sample bootstrap p05 is materially negative.
- Any lookahead or open-realism issue appears.

## Earnings Unknown

If no timestamp-safe earnings calendar exists, GAP-007 must set `earnings_unknown=true`. Extreme-gap proxy analysis is only descriptive and cannot substitute for a real timestamp-safe earnings control. Paper remains blocked if edge appears dominated by uncontrolled earnings events.

## No Promotion Rule

Even if GAP-007 survives, the result is only a research observation. Paper/shadow/live would require a later, separately authorized task with risk limits, kill switch, broker isolation, operational checks, and explicit Asier approval.
