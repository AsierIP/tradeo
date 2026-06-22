# Tradeo Intraday No-Regression Contract

Date: 2026-06-22

Intraday is additive and disabled by default. Codex changes must preserve these invariants:

1. `TRADEO_INTRADAY_ENABLED=false` registers no intraday jobs and opens no intraday execution path.
2. Daily Research -> Lab -> Director -> Production -> Fox -> Live semantics stay unchanged.
3. Existing `SignalStatus`, `TradeStatus`, and `DiscoveredPatternStatus` meanings stay unchanged.
4. Intraday data lives under explicit `intraday` metadata namespaces and session ledgers.
5. Daily risk, Director, LiveReadinessGate, and IBKRBroker safety gates are not weakened for intraday.
6. No secret values are returned by health, reports, config doctor, bundles, or audit packs.
7. Intraday live remains fail-closed unless daily live readiness is armed, calendar is enabled, and EOD flat is enabled.
8. No intraday signal may be considered executable without a session, closed-bar timestamp, expiry, and flat plan.
9. Flat confirmation must be broker-verified once execution modules are active; DB-only flat is insufficient.
10. Human approval and a later post-paper audit are required before live intraday.

Safety command:

```bash
make test-safety
```

The safety suite compiles backend code, runs quantitative/regression tests, and runs the intraday config/model/calendar/pacing tests.
