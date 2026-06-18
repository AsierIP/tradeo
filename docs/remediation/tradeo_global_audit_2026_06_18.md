# Tradeo Global Audit - 2026-06-18

## Verdict

NO-GO for live trading on 2026-06-19.

Reasons:
- US equities are closed on 2026-06-19 for Juneteenth.
- The latest Director/audit package is blocked and has no usable paper fills.
- Runtime Paper is currently blocked by IBKR connectivity and a DB-persisted runtime kill switch.
- Several audit findings could contaminate Research/Lab evidence if left unpatched.

Paper on 2026-06-18 is GO only after:
- IB Gateway/TWS Paper is logged in and reachable through `host.docker.internal:14002`.
- DB vs IBKR reconciliation is clean.
- The runtime kill switch is explicitly cleared after the divergence is understood.

## Consensus From 10 Audit Fronts

- No direct Research-to-live bypass was found.
- Live submit is centrally blocked by production pattern status, active manifest, human approval, `LiveReadinessGate`, and IBKR execution preflights.
- Evidence is not sufficient for production: current audit package reports zero paper trades/fills.
- Paper evidence is currently blocked by runtime state, not just code: IBKR is unreachable and reconciliation previously found CARG/FUBO divergence.
- Research/Lab needed tighter gates so weak or stale data cannot feed new evidence.

## Runtime State Observed

- Docker services were up and healthy.
- `.env` was in paper mode with live disabled and paper auto-submit enabled.
- Runtime kill switch was active in `system_controls`.
- Kill switch reason: reconciliation divergence between DB open trades and IBKR state.
- IBKR proxy was listening on `14002`, but no local IB Gateway/TWS socket was listening on `4002`, `7497`, `4001`, or `7496`.
- Today before the US open: zero new signals and zero new trades.

## Patches Applied

- Added OHLCV data-quality rejection inside `PatternDiscoveryLabAgent` before sampling.
- Added OHLCV data-quality rejection inside `NovelPatternMatcher._current_data` before runtime matching.
- Revalidated live submit through `RiskManager` immediately before broker connection/order preflight.
- Made Laboratory auto-submit paper orders only for `lab_candidate`; weaker Lab/watchlist states degrade to shadow observation.

## Remaining Blockers

- IBKR Paper must be reachable and logged in.
- CARG/FUBO divergence must be reconciled before clearing runtime kill switch.
- Paper ACK/order identity still needs hardening so repeated IBKR order ids cannot confuse reconciliation.
- Latest audit package must be regenerated after real paper fills.
- Nested replay / scientific gate remains blocked.
- Rollback/live runbook is not strong enough for live operation.
- Legacy `MarketScanner` and `PaperBroker` paths need stricter separation from Research/Lab/Fox.

## Verification

- Focused affected tests: 18 passed.
- Full backend tests: 571 passed, 1 skipped, 1 warning.
- Ruff on changed backend files: passed.
- `git diff --check`: passed.
