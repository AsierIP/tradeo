# DSS-004C-A Guards

Generated: 2026-07-04

## Result

Guard decision: PASS.

Checks:

- SPY/QQQ excluded from operational trades: PASS
- Fake 2026-07-03 bar absent: PASS
- last_valid_bar_date: 2026-07-02
- latest operational cache date: 2026-07-02
- Signal t, entry t+1: PASS
- Placebo rows present: PASS
- Baseline rows present: PASS
- Cache-only: PASS
- No future fields used: PASS

No orders, paper execution, live execution, cron, .env modification, or operational preview were produced.

## Artifact

- artifacts/runtime/daily_swing/dss_004c_a_guards_summary.json
