# DSS-004F-R Guard Reconfirmation

Guard result: `PASS`.

- Cache: research-150, cache-only.
- SPY/QQQ excluded from operational episodes/trades.
- Fake 2026-07-03 bar present: `false`.
- Last valid bar date: `2026-07-02`.
- Signal uses date `t`; entry is next open `t+1` or offset-relative next open.
- ATR rank uses `t-1` field in signal construction.
- Regime symbol: `SPY`; no IBKR or data downloads in rerun.

No lookahead/leakage was found in the canonical rerun path.
