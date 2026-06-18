# Tradeo LiveReadinessGate Front D - 2026-06-18

Scope: live-readiness decision record plus the Front D execution-time market
preflight follow-up. No live configuration, runtime settings, or production
manifests were changed.

## Decision

Live remains blocked unless a single `LiveReadinessGate` decision is green and
the broker submit path also proves the exact signal is a Fox/Director production
signal. Unknown, stale, missing, warning, or partially reconciled state must be
treated as not ready.

## 2026-06-18 execution-time preflight update

`IBKRBroker.submit_signal_bracket` now runs a live-only execution preflight
after LiveReadinessGate/provenance/contract qualification and before
`bracketOrder` or `placeOrder`.

Enforced now:

- regular US equity session must be open via `market_session_status()`;
- submitted bracket geometry must still be valid after operational price
  calculation;
- a same-connection IBKR `reqMktData(snapshot=True)` quote must return usable,
  non-crossed bid/ask;
- quote timestamps older than the execution preflight max age are rejected
  (default 5 seconds);
- spread, entry-quote slippage, bid/ask size, and top-of-book notional must pass
  configurable hard thresholds before any WhatIf or order construction;
- a same-connection IBKR parent-order `whatIfOrder` must return clean margin and
  commission evidence before `bracketOrder`;
- the accepted preflight evidence is stored on `Trade.metadata_json` and the
  execution observation with `data_basis=ibkr_execution_preflight_quote_snapshot`
  and `data_basis=ibkr_live_parent_order_what_if`.

The preflight is live-only. Paper order behavior is unchanged except for a
nullable metadata field.

## Execution preflight API shape

The live submit sequence is intentionally ordered as:

1. `LiveReadinessGate` and Fox/Director production provenance.
2. Contract qualification.
3. Submitted bracket geometry from operational prices.
4. Regular-session check.
5. Quote snapshot plus threshold gates.
6. Parent-order WhatIf margin/commission gates.
7. `bracketOrder` and `placeOrder`.

Execution preflight config lives in `Settings` and maps to `TRADEO_...`
environment names:

- `ibkr_execution_preflight_quote_timeout_seconds=4.0`
- `ibkr_execution_preflight_quote_max_age_seconds=5.0`
- `ibkr_execution_preflight_max_spread_pct=0.005`
- `ibkr_execution_preflight_max_spread_cost_r=0.05`
- `ibkr_execution_preflight_max_entry_slippage_pct=0.0025`
- `ibkr_execution_preflight_max_entry_slippage_r=0.10`
- `ibkr_execution_preflight_min_bid_size=100.0`
- `ibkr_execution_preflight_min_ask_size=100.0`
- `ibkr_execution_preflight_min_top_of_book_notional_usd=1000.0`
- `ibkr_execution_preflight_whatif_enabled=true`
- `ibkr_execution_preflight_max_commission_usd=5.0`
- `ibkr_execution_preflight_max_commission_r=0.05`

All numeric execution-preflight thresholds are non-negative settings. Zero is
allowed only as an explicit operator choice; missing/invalid live quote or
WhatIf facts still fail closed.

## Current code facts

- `backend/tradeo/services/live_readiness_gate.py:27` defines a central gate.
  It checks env/runtime kill switches, `live_armed`, live mode, readonly, live
  port, explicit IBKR account, non-empty allowlist, worker freshness, clean
  recent reconciliation, and active production manifest.
- `/health/deep` exposes the gate through
  `backend/tradeo/routers/health.py:56`.
- Fox status uses the same gate for `live_orders_allowed` at
  `backend/tradeo/modules/shared/entry_scanner.py:664`.
- Manual IBKR submit calls `LiveReadinessGate.require_ready(...)` for live
  targets in `backend/tradeo/services/ibkr_broker.py`, then separately
  requires `LIVE_APPROVED`, Fox metadata, production pattern status, active
  manifest, and the execution-time preflight before `bracketOrder` or
  `placeOrder`.
- Reconciliation writes the freshness evidence the gate reads, and auto-kills
  on confirmed DB/broker divergence at
  `backend/tradeo/services/reconciliation.py:979` and
  `backend/tradeo/services/reconciliation.py:997`.

## Hard gates

1. **Global live arming and broker target**
   - Must require: env kill off, runtime kill off, `live_armed=true`,
     `trading_mode=live`, IBKR live port, `ibkr_readonly=false`, explicit
     account, and non-empty symbol allowlist.
   - Why: prevents accidental live routing through paper/research defaults,
     readonly mode, account ambiguity, or allow-all symbol scope.
   - Verify: one test per block reason plus `/health/deep` snapshot asserting
     `orders_allowed=false` and the expected `primary_block_reason`.

2. **Single gate authority on every live order surface**
   - Must require: scheduler/Fox status and manual `/ibkr/.../submit-bracket`
     both call `LiveReadinessGate.require_ready` before broker placement.
   - Why: live readiness cannot diverge between dashboard, scanner, API, and
     broker adapter.
   - Verify: submit tests with stale reconciliation, stale worker heartbeat,
     runtime kill switch, missing allowlist, and missing manifest all fail
     before `placeOrder`.
   - Open decision: current manual submit uses `require_auto_submit=False`. If
     `fox_hunter_auto_submit_live_orders=false` is intended to mean "no live
     orders at all", make it hard for manual too. If manual live is allowed,
     add an explicit `manual_live_submit_enabled`/human-intent gate so this is
     not an accidental bypass.

3. **Production provenance**
   - Must require: `LIVE_APPROVED` signal, `entry_module=fox_hunter`, existing
     discovered pattern, `status=production`, canonical unexpired
     `DirectorProductionGate` manifest, valid manifest hash, and complete
     normal IBKR paper-fill evidence packet.
   - Why: research, Lab, legacy scanner, shadow, or paper-approved evidence must
     never be enough for live money.
   - Verify: live submit rejects Lab, legacy, `paper_approved`, missing pattern,
     non-production pattern, expired manifest, hash mismatch, and incomplete
     evidence packet.

4. **Reconciliation freshness and cleanliness**
   - Must require: latest reconciliation completed successfully, broker was
     reachable, zero divergences, zero warnings, zero exit-protection errors,
     and the clean run is newer than live arming and the current worker start.
   - Why: a clean row from before restart or before an operator arms live can be
     stale while DB/broker state has already diverged.
   - Verify: missing row, stale row, warning row, divergence row,
     broker-unreachable result, and clean row older than worker heartbeat all
     block readiness.

5. **Worker and job health**
   - Must require: fresh worker heartbeat, scheduler enabled, Fox job healthy,
     reconciliation job healthy, and no recent job exception for live-critical
     tasks.
   - Why: heartbeat freshness alone proves the loop is alive, not that the jobs
     feeding readiness and reconciliation are succeeding.
   - Verify: stale heartbeat, scheduler disabled, last Fox failure, and last
     reconciliation failure each block `orders_allowed`.

6. **Broker-synced risk**
   - Must require: daily/monthly PnL, NetLiquidation/AvailableFunds, open
     orders, open positions, and gross exposure are synced from IBKR plus DB
     before sizing.
   - Why: `backend/tradeo/services/risk_manager.py:40` still documents equity
     as configured capital plus ledger until broker sync; this is not enough
     for live loss/exposure hard stops.
   - Verify: broker closed loss updates risk state and trips daily/monthly
     limits; broker-only open position contributes to exposure or blocks via
     reconciliation; new order notional is checked against cumulative exposure.

7. **Post-live decay and drift**
   - Must require: `live_fill` evidence participates in production health
     monitoring, and any `drift_status` in `decaying`, `degrading`,
     `regressing`, or `deteriorating` blocks new Fox matches/manifests.
   - Why: current production health code selects trades through the Director
     paper-fill predicate, while real live degradation must shut the gate too.
   - Verify: synthetic live fills trigger health decay; a decaying production
     pattern is excluded by matcher/manifest checks and cannot submit live.

8. **Execution-time market safety**
   - Must require: regular session open unless an explicit after-hours mode
     exists, valid submitted bracket geometry, fresh non-crossed bid/ask, quote
     age <= `ibkr_execution_preflight_quote_max_age_seconds`, spread <=
     `ibkr_execution_preflight_max_spread_pct`, spread cost <=
     `ibkr_execution_preflight_max_spread_cost_r`, entry quote slippage <= both
     `ibkr_execution_preflight_max_entry_slippage_pct` and
     `ibkr_execution_preflight_max_entry_slippage_r`, bid/ask sizes >=
     `ibkr_execution_preflight_min_bid_size` /
     `ibkr_execution_preflight_min_ask_size`, and top-of-book notional >=
     `ibkr_execution_preflight_min_top_of_book_notional_usd`.
   - Why: a green readiness gate is not enough if the actionable quote, fill
     price implied by the top of book, or immediate liquidity has moved outside
     the edge budget.
   - Verify: closed market, missing bid/ask, stale quote, wide spread, low
     top-of-book liquidity, and persisted accepted quote evidence all execute
     before `bracketOrder`/`placeOrder`.

9. **WhatIf margin and commission safety**
   - Must require: `ibkr_execution_preflight_whatif_enabled=true`; IBKR
     `whatIfOrder` on the parent submitted-entry order returns no warning text;
     status is not `Inactive`, `Rejected`, `Cancelled`, or `ApiError`; finite
     `initMarginBefore/Change/After`, `maintMarginBefore/Change/After`, and
     `equityWithLoanBefore/Change/After`; `equityWithLoanAfter > 0`;
     `initMarginAfter` and `maintMarginAfter` do not exceed
     `equityWithLoanAfter`; commission/min/max commission are non-negative; max
     observed commission <= `ibkr_execution_preflight_max_commission_usd`; and
     commission R <= `ibkr_execution_preflight_max_commission_r`.
   - Why: account-readiness pings prove connectivity, not order affordability
     or commission drag. WhatIf is the last broker-native dry run before live
     order construction.
   - Verify: WhatIf warning and over-limit commission block before bracket
     creation, while accepted evidence is persisted with
     `data_basis=ibkr_live_parent_order_what_if`.

## Verification package

Recommended focused tests when code ownership is clear:

- `backend/tradeo/tests/test_live_readiness_gate.py`: pure gate matrix for each
  block reason, including reconciliation age and worker age.
- Submit integration test: live manual submit never calls `placeOrder` unless
  `LiveReadinessGate`, Fox production provenance, market session, bracket
  geometry, and fresh quote preflight pass.
- Worker/reconciliation test: readiness blocks if the latest clean
  reconciliation predates current worker start or live arming.
- Risk test: broker-synced losses and cumulative exposure drive hard stops.
- Health monitor test: `live_fill` decay blocks future Fox eligibility.

Focused tests were added in
`backend/tradeo/tests/test_execution_state_transitions.py` for closed market,
missing bid/ask, stale quote, wide spread, spread cost R, entry quote
slippage, low bid/ask size, low top-of-book notional, WhatIf warning, high
WhatIf commission, missing/invalid WhatIf margin or commission fields, WhatIf
API failure, paper-mode preflight skip, and persisted fresh quote/WhatIf
evidence.

Evidence run:

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_execution_state_transitions.py -q`
  -> `87 passed in 35.53s`
- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_ibkr_broker_preflight.py -q`
  -> `5 passed in 7.37s`

## Explicit Non-goals

- This does not arm live trading, change `.env`, change runtime kill switches,
  or alter production manifests.
- This does not introduce after-hours or pre-market live execution; regular
  session remains the only allowed live execution session.
- This does not make thresholds per-symbol, per-regime, or dynamically
  calibrated. The current API is a global hard threshold surface that future
  calibration can tune from observed quote/fill distributions.
- This does not replace broker-synced daily/monthly loss, exposure, open-order,
  or open-position controls; those remain separate live-risk gates.
- `/health/ibkr/live-preflight` remains a non-order account/connectivity check.
  WhatIf order previews are part of live submit, not the health endpoint.
- Manual live submit still uses `require_auto_submit=False`; an explicit
  `manual_live_submit_enabled` decision remains open if manual live should be
  separated from Fox auto-submit.

## Files Changed

- `backend/tradeo/core/config.py`
- `backend/tradeo/services/ibkr_broker.py`
- `backend/tradeo/tests/test_execution_state_transitions.py`
- `docs/remediation/tradeo_live_readiness_gate_front_d_2026_06_18.md`
