# DSS-GAP-001 Context

Task: T-DAILY-GAP-001
Generated: 2026-07-05

## Terminal Daily Context

The current Daily PB/BO/CO/CW line is closed. It produced reusable research infrastructure, but no Daily shadow, paper, or live candidate.

Terminal decisions used for this protocol:

- DSS-PB-001: research fail after OOS/cost review.
- DSS-BO-001: baseline explained fail; breakout edge was not independent.
- DSS-CO-001: timing/effective-sample warning; not an operational candidate.
- DSS-CW-001: timing not specific fail; timing placebos dominated the base.

This protocol must not rescue PB/BO/CO/CW, must not create DSS-005, and must not reinterpret prior positive-looking metrics as operational approval.

## Roadmap Context

T-DAILY-ROADMAP-001 selected `gap continuation / gap reversal` as the next Daily search-space because it:

- uses existing Daily OHLCV fields;
- does not require external datasets for the protocol phase;
- can be audited with explicit open-realism, delayed-entry, sign-inversion, and matched non-gap controls;
- is distinct from PB/BO/CO/CW.

The roadmap did not authorize a backtest. It only authorized protocol and scaffold work.

## Reusable Infrastructure

The main branch preserves:

- Daily OHLCV cache/read-only tooling;
- stock-only universe and SPY/QQQ benchmark-only policy;
- quality gates;
- cache-only historical research tooling;
- no-lookahead and calendar guards;
- cost/OOS metrics;
- placebo, matched-baseline, timing, overlap, concentration, and effective-sample audits;
- FDR/WRC/SPA-light research-only checks;
- focal Daily tests.

## Safety Position

DSS-GAP-001 starts as a research protocol only. It is not a paper candidate, not a shadow candidate, not a signal source, and not an order surface.
