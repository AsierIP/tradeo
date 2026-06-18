# Tradeo LiveReadinessGate Front D - 2026-06-18

Scope: static audit and decision record only. No live configuration, order
routing, runtime settings, or production manifests were changed.

## Decision

Live remains blocked unless a single `LiveReadinessGate` decision is green and
the broker submit path also proves the exact signal is a Fox/Director production
signal. Unknown, stale, missing, warning, or partially reconciled state must be
treated as not ready.

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
  targets at `backend/tradeo/services/ibkr_broker.py:330`, then separately
  requires `LIVE_APPROVED`, Fox metadata, production pattern status, and active
  manifest at `backend/tradeo/services/ibkr_broker.py:316` and
  `backend/tradeo/services/ibkr_broker.py:336`.
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
   - Must require for automated live submit: regular session open unless an
     explicit after-hours mode exists, fresh quote/spread snapshot, valid bracket
     geometry, acceptable spread/slippage/liquidity, and successful what-if or
     equivalent preflight when IBKR supports it.
   - Why: a green readiness gate is not enough if the actionable quote or market
     session has gone stale.
   - Verify: stale quote, closed market, excessive spread, invalid bracket, and
     failed preflight each block before order placement.

## Verification package

Recommended focused tests when code ownership is clear:

- `backend/tradeo/tests/test_live_readiness_gate.py`: pure gate matrix for each
  block reason, including reconciliation age and worker age.
- Submit integration test: live manual submit never calls `placeOrder` unless
  both `LiveReadinessGate` and Fox production provenance pass.
- Worker/reconciliation test: readiness blocks if the latest clean
  reconciliation predates current worker start or live arming.
- Risk test: broker-synced losses and cumulative exposure drive hard stops.
- Health monitor test: `live_fill` decay blocks future Fox eligibility.

No tests were added in this pass because the requested deliverable was a
doc-only audit/decision record and the current gate implementation is already
being changed in source files outside this Front D ownership.
